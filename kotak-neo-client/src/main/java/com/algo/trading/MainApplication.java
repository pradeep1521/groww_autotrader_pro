package com.algo.trading;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Execution entry point for the Kotak Neo API client.
 *
 * <p><b>All secrets MUST be supplied via environment variables</b>; never
 * hard-code credentials in source. Set the following before running:
 *
 * <pre>{@code
 *   export KOTAK_CONSUMER_KEY="<your developer consumer key>"
 *   export KOTAK_USERNAME="<your Kotak Neo login ID>"
 *   export KOTAK_PASSWORD="<your Kotak Neo password>"
 *   export KOTAK_TOTP_SEED="<base-32 seed from your authenticator app>"
 * }</pre>
 *
 * <p>Run with the fat-jar produced by {@code mvn package}:
 * <pre>{@code
 *   java -jar target/kotak-neo-client-1.0.0.jar
 * }</pre>
 */
public class MainApplication {

    private static final Logger log = LoggerFactory.getLogger(MainApplication.class);

    public static void main(String[] args) {
        // ── 1. Load secrets from environment variables ────────────────────────
        String consumerKey = requireEnv("KOTAK_CONSUMER_KEY");
        String username    = requireEnv("KOTAK_USERNAME");
        String password    = requireEnv("KOTAK_PASSWORD");
        String totpSeed    = requireEnv("KOTAK_TOTP_SEED");

        // ── 2. Construct the client; use try-with-resources to ensure cleanup ─
        try (KotakNeoClient client = new KotakNeoClient(consumerKey, username, password, totpSeed);
             SessionManager  sessionManager = new SessionManager(client)) {

            // ── 3. Authenticate and start the keep-alive scheduler ────────────
            client.login();
            sessionManager.start();

            // ── 4. Build a type-safe order via the fluent builder ─────────────
            //       Intraday market order: BUY 10 shares of Reliance on NSE
            OrderRequest order = new OrderRequest.Builder()
                    .exchange(OrderRequest.Exchange.NSE)
                    .tradingSymbol("RELIANCE-EQ")
                    .transactionType(OrderRequest.TransactionType.BUY)
                    .orderType(OrderRequest.OrderType.MARKET)
                    .productType(OrderRequest.ProductType.MIS)
                    .quantity(10)
                    .validity(OrderRequest.Validity.DAY)
                    .tag("algo-boot-demo")
                    .build();

            // ── 5. Submit the order ───────────────────────────────────────────
            log.info("Submitting BUY 10 x RELIANCE-EQ (MKT / MIS / DAY)…");
            String rawResponse = client.placeOrder(order.toMap());

            // ── 6. Parse and log the exchange receipt ─────────────────────────
            printOrderReceipt(rawResponse);

            // ── 7. (Optional) Poll order status after a brief wait ────────────
            String orderId = extractOrderId(rawResponse);
            if (orderId != null) {
                log.info("Fetching order status for ID: {}", orderId);
                String statusJson = client.getOrderStatus(orderId);
                log.info("Order status: {}", statusJson);
            }

        } catch (KotakNeoApiException ex) {
            log.error("[API ERROR] {}", ex.getMessage(), ex);
            System.exit(1);
        } catch (Exception ex) {
            log.error("[UNEXPECTED ERROR] Execution halted: {}", ex.getMessage(), ex);
            System.exit(2);
        }
    }

    // --------------------------------------------------------------------------
    // Helpers
    // --------------------------------------------------------------------------

    /**
     * Reads a mandatory environment variable. Exits with a clear error if absent
     * rather than throwing a NullPointerException deep in the call stack.
     */
    private static String requireEnv(String name) {
        String value = System.getenv(name);
        if (value == null || value.isBlank()) {
            System.err.println("[STARTUP ERROR] Required environment variable '" + name + "' is not set.");
            System.exit(3);
        }
        return value;
    }

    private static void printOrderReceipt(String rawJson) {
        try {
            ObjectMapper mapper = new ObjectMapper();
            JsonNode root = mapper.readTree(rawJson);
            log.info("=== Order Receipt ===");
            log.info("  Order ID   : {}", root.path("data").path("nOrdNo").asText("(not present)"));
            log.info("  Status     : {}", root.path("data").path("ordSt").asText("(not present)"));
            log.info("  Message    : {}", root.path("data").path("rejRsn").asText("N/A"));
            log.info("=====================");
        } catch (Exception ex) {
            log.warn("Could not parse order receipt JSON; raw response: {}", rawJson);
        }
    }

    private static String extractOrderId(String rawJson) {
        try {
            ObjectMapper mapper = new ObjectMapper();
            JsonNode root = mapper.readTree(rawJson);
            String id = root.path("data").path("nOrdNo").asText(null);
            return (id != null && !id.isBlank()) ? id : null;
        } catch (Exception ex) {
            return null;
        }
    }
}
