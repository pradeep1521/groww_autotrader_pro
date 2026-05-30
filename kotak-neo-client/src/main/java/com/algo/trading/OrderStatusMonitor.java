package com.algo.trading;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Objects;
import java.util.Optional;

/**
 * Utility for parsing and monitoring Kotak Neo order fulfillment responses.
 *
 * <p>The exchange echoes back a status code on every order operation.
 * This class centralises the mapping from raw JSON to a typed {@link OrderStatus}
 * record so that strategy code never has to touch raw string literals.
 *
 * <p>Usage:
 * <pre>{@code
 *   String rawJson = client.getOrderStatus(orderId);
 *   Optional<OrderStatus> status = OrderStatusMonitor.parse(rawJson);
 *   status.ifPresent(s -> {
 *       if (s.isFilled()) { … }
 *   });
 * }</pre>
 */
public final class OrderStatusMonitor {

    private static final Logger log = LoggerFactory.getLogger(OrderStatusMonitor.class);
    private static final ObjectMapper MAPPER = new ObjectMapper();

    private OrderStatusMonitor() { /* utility class */ }

    // --------------------------------------------------------------------------
    // Kotak Neo terminal order states (from official documentation)
    // --------------------------------------------------------------------------

    public enum State {
        /** Order fully executed on the exchange. */
        COMPLETE,
        /** Order open and waiting for a counterparty. */
        OPEN,
        /** Waiting for exchange acknowledgement. */
        PENDING,
        /** Order cancelled by the client or broker. */
        CANCELLED,
        /** Order rejected by the exchange or RMS. */
        REJECTED,
        /** Partial fill – some but not all lots executed. */
        PARTIALLY_FILLED,
        /** Unrecognised state string from the API. */
        UNKNOWN;

        /**
         * Maps the raw status string returned by Kotak Neo to this enum.
         *
         * @param raw the {@code ordSt} field value from the API response
         */
        public static State fromApiCode(String raw) {
            if (raw == null) return UNKNOWN;
            return switch (raw.trim().toUpperCase()) {
                case "COMPLETE",  "FILLED"           -> COMPLETE;
                case "OPEN",      "OPN"              -> OPEN;
                case "PENDING",   "PUT ORDER REQ RECEIVED" -> PENDING;
                case "CANCELLED", "CANCEL"           -> CANCELLED;
                case "REJECTED",  "REJ"              -> REJECTED;
                case "PARTIAL FILL", "PARTIAL_FILL"  -> PARTIALLY_FILLED;
                default -> {
                    log.warn("Unknown order state code received from API: '{}'", raw);
                    yield UNKNOWN;
                }
            };
        }
    }

    // --------------------------------------------------------------------------
    // Value type
    // --------------------------------------------------------------------------

    /**
     * Structured representation of a single order status record.
     *
     * @param orderId       unique order number assigned by the exchange
     * @param state         interpreted {@link State}
     * @param rawState      original {@code ordSt} field as returned by the API
     * @param tradingSymbol the instrument (e.g., {@code RELIANCE-EQ})
     * @param quantity      total ordered quantity
     * @param filledQty     quantity that has been executed so far
     * @param averagePrice  weighted average execution price (0 if not yet filled)
     * @param rejectReason  rejection message if state is {@link State#REJECTED}
     */
    public record OrderStatus(
            String orderId,
            State  state,
            String rawState,
            String tradingSymbol,
            int    quantity,
            int    filledQty,
            double averagePrice,
            String rejectReason
    ) {
        /** Returns {@code true} when the order has been fully executed. */
        public boolean isFilled()    { return state == State.COMPLETE; }

        /** Returns {@code true} while the order is live on the exchange. */
        public boolean isOpen()      { return state == State.OPEN || state == State.PARTIALLY_FILLED; }

        /** Returns {@code true} for any terminal failure state. */
        public boolean isTerminal()  {
            return state == State.COMPLETE || state == State.CANCELLED || state == State.REJECTED;
        }

        @Override
        public String toString() {
            return String.format(
                    "OrderStatus[id=%s, state=%s, symbol=%s, qty=%d, filled=%d, avgPx=%.2f, rejRsn=%s]",
                    orderId, state, tradingSymbol, quantity, filledQty, averagePrice, rejectReason);
        }
    }

    // --------------------------------------------------------------------------
    // Parsing
    // --------------------------------------------------------------------------

    /**
     * Parses a raw Kotak Neo order-report JSON response.
     *
     * @param rawJson the {@link String} returned by {@link KotakNeoClient#getOrderStatus}
     * @return an {@link Optional} containing the parsed status, or empty on parse failure
     */
    public static Optional<OrderStatus> parse(String rawJson) {
        Objects.requireNonNull(rawJson, "rawJson must not be null");
        try {
            JsonNode root = MAPPER.readTree(rawJson);
            JsonNode data = root.path("data");

            if (data.isMissingNode()) {
                log.warn("Order status response contains no 'data' node. Body: {}", rawJson);
                return Optional.empty();
            }

            String orderId      = data.path("nOrdNo").asText(null);
            String rawState     = data.path("ordSt").asText(null);
            String symbol       = data.path("trdSym").asText("UNKNOWN");
            int    qty          = parseInt(data.path("qty").asText("0"));
            int    filledQty    = parseInt(data.path("fldQty").asText("0"));
            double avgPx        = parseDouble(data.path("avgPrc").asText("0"));
            String rejectReason = data.path("rejRsn").asText(null);

            State state = State.fromApiCode(rawState);

            OrderStatus status = new OrderStatus(
                    orderId, state, rawState, symbol, qty, filledQty, avgPx, rejectReason);

            log.debug("Parsed: {}", status);
            return Optional.of(status);

        } catch (Exception ex) {
            log.error("Failed to parse order status JSON: {}", ex.getMessage());
            log.debug("Problematic JSON: {}", rawJson);
            return Optional.empty();
        }
    }

    // --------------------------------------------------------------------------
    // Private utilities
    // --------------------------------------------------------------------------

    private static int parseInt(String value) {
        try { return Integer.parseInt(value.trim()); }
        catch (NumberFormatException ex) { return 0; }
    }

    private static double parseDouble(String value) {
        try { return Double.parseDouble(value.trim()); }
        catch (NumberFormatException ex) { return 0.0; }
    }
}
