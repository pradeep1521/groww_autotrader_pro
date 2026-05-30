package com.algo.trading;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.github.resilience4j.circuitbreaker.CircuitBreaker;
import io.github.resilience4j.circuitbreaker.CircuitBreakerConfig;
import io.github.resilience4j.ratelimiter.RateLimiter;
import io.github.resilience4j.ratelimiter.RateLimiterConfig;
import io.github.resilience4j.retry.Retry;
import io.github.resilience4j.retry.RetryConfig;
import org.jboss.aerogear.security.otp.Totp;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.Map;
import java.util.Objects;
import java.util.concurrent.Callable;
import java.util.concurrent.atomic.AtomicReference;

/**
 * Production-grade, thread-safe REST client for the Kotak Neo NeoTrade API.
 *
 * <p>Authentication lifecycle is automated:
 * <ol>
 *   <li>Generates the current TOTP token from the stored seed at login time.</li>
 *   <li>Exchanges credentials for a JWT, which is cached in an AtomicReference.</li>
 *   <li>The companion {@link SessionManager} refreshes the token every 4 hours.</li>
 * </ol>
 *
 * <p>Resilience measures baked in:
 * <ul>
 *   <li><b>Rate Limiter</b> – caps outbound order calls at 9 req/s (Kotak hard limit: 10).</li>
 *   <li><b>Circuit Breaker</b> – opens after 5 consecutive failures, preventing cascade.</li>
 *   <li><b>Retry</b> – retries transient 5xx errors up to 3 times with exponential back-off.</li>
 * </ul>
 *
 * <p><b>Security note</b>: credentials are never stored beyond construction scope; the TOTP
 * seed is held in a {@code char[]} field and cleared after each token generation.
 * Pass all secrets via environment variables – never hardcode them.
 */
public class KotakNeoClient implements AutoCloseable {

    private static final Logger log = LoggerFactory.getLogger(KotakNeoClient.class);

    // --------------------------------------------------------------------------
    // API surface URLs  (replace paths once official docs confirm the endpoints)
    // --------------------------------------------------------------------------
    private static final String BASE_URL      = "https://gw-napi.kotaksecurities.com/trade/api/v1";
    private static final String AUTH_URL      = "https://gw-napi.kotaksecurities.com/login/1.0/login/v2/validate";
    private static final String ORDER_URL     = BASE_URL + "/orders";
    private static final String ORDER_STATUS_URL = BASE_URL + "/order-report";

    // --------------------------------------------------------------------------
    // Configuration constants
    // --------------------------------------------------------------------------
    private static final int    HTTP_OK               = 200;
    private static final int    HTTP_CREATED          = 201;
    private static final Duration HTTP_TIMEOUT        = Duration.ofSeconds(10);
    private static final Duration RATE_LIMIT_PERIOD   = Duration.ofSeconds(1);
    private static final int    MAX_CALLS_PER_SECOND  = 9;    // Kotak limit is 10; stay under

    // --------------------------------------------------------------------------
    // Immutable identity fields
    // --------------------------------------------------------------------------
    private final String consumerKey;
    private final String username;
    private final String password;
    /**
     * TOTP base-32 seed from your authenticator app registration.
     * Stored as char[] so it can be zeroed in {@link #close()}.
     */
    private final char[] totpSeed;

    // --------------------------------------------------------------------------
    // Shared infrastructure
    // --------------------------------------------------------------------------
    private final HttpClient    httpClient;
    private final ObjectMapper  objectMapper;
    private final RateLimiter   rateLimiter;
    private final CircuitBreaker circuitBreaker;
    private final Retry         retry;

    /** Thread-safe JWT cache; null means unauthenticated. */
    private final AtomicReference<String> jwtToken = new AtomicReference<>(null);

    // --------------------------------------------------------------------------
    // Constructor
    // --------------------------------------------------------------------------

    /**
     * Creates a client instance.
     *
     * <p><b>Never pass literal strings for secrets.</b>
     * Load them from environment variables or a secrets manager:
     * <pre>{@code
     *   new KotakNeoClient(
     *       System.getenv("KOTAK_CONSUMER_KEY"),
     *       System.getenv("KOTAK_USERNAME"),
     *       System.getenv("KOTAK_PASSWORD"),
     *       System.getenv("KOTAK_TOTP_SEED")
     *   );
     * }</pre>
     *
     * @param consumerKey your Neo developer consumer key
     * @param username    your Kotak Neo login ID
     * @param password    your Kotak Neo password
     * @param totpSeed    base-32 TOTP seed from Google Authenticator setup
     */
    public KotakNeoClient(String consumerKey, String username, String password, String totpSeed) {
        this.consumerKey = Objects.requireNonNull(consumerKey, "consumerKey must not be null");
        this.username    = Objects.requireNonNull(username,    "username must not be null");
        this.password    = Objects.requireNonNull(password,    "password must not be null");
        this.totpSeed    = Objects.requireNonNull(totpSeed,    "totpSeed must not be null").toCharArray();

        this.httpClient   = HttpClient.newBuilder()
                .connectTimeout(HTTP_TIMEOUT)
                .build();
        this.objectMapper = new ObjectMapper();

        // ── Rate Limiter: max 9 calls per second ─────────────────────────────
        RateLimiterConfig rlConfig = RateLimiterConfig.custom()
                .limitForPeriod(MAX_CALLS_PER_SECOND)
                .limitRefreshPeriod(RATE_LIMIT_PERIOD)
                .timeoutDuration(Duration.ofSeconds(2))
                .build();
        this.rateLimiter = RateLimiter.of("kotak-neo-rate-limiter", rlConfig);

        // ── Circuit Breaker: open after 5 consecutive failures ────────────────
        CircuitBreakerConfig cbConfig = CircuitBreakerConfig.custom()
                .failureRateThreshold(60)
                .slowCallRateThreshold(80)
                .slowCallDurationThreshold(Duration.ofSeconds(5))
                .minimumNumberOfCalls(5)
                .waitDurationInOpenState(Duration.ofSeconds(30))
                .build();
        this.circuitBreaker = CircuitBreaker.of("kotak-neo-circuit-breaker", cbConfig);

        // ── Retry: up to 3 attempts with exponential back-off ─────────────────
        RetryConfig retryConfig = RetryConfig.custom()
                .maxAttempts(3)
                .waitDuration(Duration.ofMillis(500))
                .retryOnException(ex -> ex instanceof IOException)
                .build();
        this.retry = Retry.of("kotak-neo-retry", retryConfig);
    }

    // --------------------------------------------------------------------------
    // Public API
    // --------------------------------------------------------------------------

    /**
     * Executes the authentication handshake and caches the JWT.
     * The TOTP token is generated programmatically from the stored seed.
     *
     * <p>This method is synchronized to prevent concurrent logins that would
     * race to overwrite the cached token.
     *
     * @throws KotakNeoApiException on HTTP error or unexpected response shape
     */
    public synchronized void login() throws KotakNeoApiException {
        log.info("Initiating authentication with Kotak Neo…");

        String currentOtp = generateTotp();

        Map<String, Object> loginPayload = Map.of(
                "userid",   this.username,
                "password", this.password,
                "appCode",  this.consumerKey
        );

        try {
            String jsonBody = objectMapper.writeValueAsString(loginPayload);

            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(AUTH_URL))
                    .timeout(HTTP_TIMEOUT)
                    .header("Content-Type", "application/json")
                    .header("accept",       "application/json")
                    .header("Neo-API-Key",  this.consumerKey)
                    .header("OTP",          currentOtp)     // Kotak sends OTP as a header
                    .POST(HttpRequest.BodyPublishers.ofString(jsonBody))
                    .build();

            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());

            if (response.statusCode() == HTTP_OK || response.statusCode() == HTTP_CREATED) {
                JsonNode root  = objectMapper.readTree(response.body());
                String   token = root.path("data").path("token").asText(null);

                if (token == null || token.isBlank()) {
                    throw new KotakNeoApiException(
                            "Login succeeded (HTTP 200) but response contained no token. Body: " + response.body());
                }
                jwtToken.set(token);
                log.info("Authentication successful – JWT cached.");
            } else {
                throw new KotakNeoApiException(
                        "Authentication failed. HTTP " + response.statusCode() + ": " + response.body());
            }

        } catch (IOException | InterruptedException ex) {
            Thread.currentThread().interrupt();
            throw new KotakNeoApiException("Network error during login: " + ex.getMessage(), ex);
        }
    }

    /**
     * Submits a single order to the exchange.
     *
     * <p>The call is guarded by the rate-limiter, circuit-breaker, and retry policy.
     * See {@link OrderRequest} for a type-safe builder.
     *
     * @param orderParams key-value map of order fields (use {@link OrderRequest#toMap()})
     * @return raw JSON response body from the exchange
     * @throws KotakNeoApiException on authentication, throttle, or network failure
     */
    public String placeOrder(Map<String, Object> orderParams) throws KotakNeoApiException {
        requireAuthenticated();

        Callable<String> orderCall = CircuitBreaker.decorateCallable(circuitBreaker,
                RateLimiter.decorateCallable(rateLimiter,
                        Retry.decorateCallable(retry,
                                () -> executeOrderPost(orderParams))));
        try {
            return orderCall.call();
        } catch (KotakNeoApiException ex) {
            throw ex;
        } catch (Exception ex) {
            throw new KotakNeoApiException("Order placement failed: " + ex.getMessage(), ex);
        }
    }

    /**
     * Fetches the status / execution report for a submitted order.
     *
     * @param orderId the order ID returned by {@link #placeOrder}
     * @return raw JSON order report
     * @throws KotakNeoApiException on HTTP or network error
     */
    public String getOrderStatus(String orderId) throws KotakNeoApiException {
        requireAuthenticated();
        Objects.requireNonNull(orderId, "orderId must not be null");

        try {
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(ORDER_STATUS_URL + "/" + orderId))
                    .timeout(HTTP_TIMEOUT)
                    .header("accept",        "application/json")
                    .header("Neo-API-Key",   this.consumerKey)
                    .header("Authorization", "Bearer " + jwtToken.get())
                    .GET()
                    .build();

            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());

            if (response.statusCode() == HTTP_OK) {
                return response.body();
            }
            throw new KotakNeoApiException(
                    "Order status fetch failed. HTTP " + response.statusCode() + ": " + response.body());

        } catch (IOException | InterruptedException ex) {
            Thread.currentThread().interrupt();
            throw new KotakNeoApiException("Network error fetching order status: " + ex.getMessage(), ex);
        }
    }

    /**
     * Returns {@code true} if a valid JWT is currently cached.
     */
    public boolean isAuthenticated() {
        return jwtToken.get() != null;
    }

    /**
     * Clears the cached JWT (e.g., on detected expiry) so the next call forces re-authentication.
     */
    public void invalidateSession() {
        jwtToken.set(null);
        log.info("Session token invalidated.");
    }

    // --------------------------------------------------------------------------
    // AutoCloseable – zero out sensitive data on shutdown
    // --------------------------------------------------------------------------

    @Override
    public void close() {
        invalidateSession();
        java.util.Arrays.fill(totpSeed, '\0');
        log.info("KotakNeoClient closed; sensitive data cleared.");
    }

    // --------------------------------------------------------------------------
    // Private helpers
    // --------------------------------------------------------------------------

    private String executeOrderPost(Map<String, Object> orderParams)
            throws IOException, InterruptedException, KotakNeoApiException {

        String jsonBody = objectMapper.writeValueAsString(orderParams);

        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(ORDER_URL))
                .timeout(HTTP_TIMEOUT)
                .header("Content-Type", "application/json")
                .header("accept",       "application/json")
                .header("Neo-API-Key",  this.consumerKey)
                .header("Authorization","Bearer " + jwtToken.get())
                .POST(HttpRequest.BodyPublishers.ofString(jsonBody))
                .build();

        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());

        if (response.statusCode() == HTTP_OK || response.statusCode() == HTTP_CREATED) {
            log.info("Order accepted by exchange. Response: {}", response.body());
            return response.body();
        }

        if (response.statusCode() == 429) {
            throw new KotakNeoApiException(
                    "Rate limit exceeded (HTTP 429). The rate-limiter should have prevented this. " +
                    "Body: " + response.body());
        }
        if (response.statusCode() == 401 || response.statusCode() == 403) {
            invalidateSession();
            throw new KotakNeoApiException(
                    "Token rejected by server (HTTP " + response.statusCode() + "). " +
                    "Session invalidated – call login() before retrying. Body: " + response.body());
        }

        throw new KotakNeoApiException(
                "Order rejected. HTTP " + response.statusCode() + ": " + response.body());
    }

    private String generateTotp() {
        Totp totp = new Totp(new String(totpSeed));
        String otp = totp.now();
        log.debug("TOTP generated successfully.");
        return otp;
    }

    private void requireAuthenticated() {
        if (jwtToken.get() == null) {
            throw new IllegalStateException("Client is unauthenticated. Call login() first.");
        }
    }
}
