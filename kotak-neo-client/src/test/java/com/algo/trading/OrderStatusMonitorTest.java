package com.algo.trading;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

import java.util.Map;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;

class OrderStatusMonitorTest {

    // ── Parse happy-path ──────────────────────────────────────────────────────

    @Test
    void parse_completeOrder_returnsFilledStatus() {
        String json = """
                {
                  "data": {
                    "nOrdNo": "230001234567",
                    "ordSt": "complete",
                    "trdSym": "RELIANCE-EQ",
                    "qty": "10",
                    "fldQty": "10",
                    "avgPrc": "2850.50",
                    "rejRsn": null
                  }
                }
                """;

        Optional<OrderStatusMonitor.OrderStatus> result = OrderStatusMonitor.parse(json);

        assertTrue(result.isPresent());
        OrderStatusMonitor.OrderStatus status = result.get();
        assertEquals("230001234567", status.orderId());
        assertEquals(OrderStatusMonitor.State.COMPLETE, status.state());
        assertTrue(status.isFilled());
        assertFalse(status.isOpen());
        assertTrue(status.isTerminal());
        assertEquals(10, status.filledQty());
        assertEquals(2850.50, status.averagePrice(), 0.001);
    }

    @Test
    void parse_rejectedOrder_returnsRejectedStateWithReason() {
        String json = """
                {
                  "data": {
                    "nOrdNo": "230001234568",
                    "ordSt": "REJ",
                    "trdSym": "RELIANCE-EQ",
                    "qty": "10",
                    "fldQty": "0",
                    "avgPrc": "0",
                    "rejRsn": "Insufficient funds"
                  }
                }
                """;

        Optional<OrderStatusMonitor.OrderStatus> result = OrderStatusMonitor.parse(json);

        assertTrue(result.isPresent());
        assertEquals(OrderStatusMonitor.State.REJECTED, result.get().state());
        assertEquals("Insufficient funds", result.get().rejectReason());
        assertTrue(result.get().isTerminal());
    }

    @Test
    void parse_missingDataNode_returnsEmpty() {
        Optional<OrderStatusMonitor.OrderStatus> result =
                OrderStatusMonitor.parse("{\"status\":\"error\"}");
        assertTrue(result.isEmpty());
    }

    @Test
    void parse_malformedJson_returnsEmpty() {
        Optional<OrderStatusMonitor.OrderStatus> result =
                OrderStatusMonitor.parse("{NOT_VALID_JSON");
        assertTrue(result.isEmpty());
    }

    // ── State mapping ─────────────────────────────────────────────────────────

    @ParameterizedTest
    @CsvSource({
        "complete,        COMPLETE",
        "FILLED,          COMPLETE",
        "OPN,             OPEN",
        "OPEN,            OPEN",
        "PENDING,         PENDING",
        "CANCELLED,       CANCELLED",
        "REJ,             REJECTED",
        "PARTIAL FILL,    PARTIALLY_FILLED",
        "PARTIAL_FILL,    PARTIALLY_FILLED",
        "SOME_NEW_CODE,   UNKNOWN"
    })
    void stateFromApiCode_mapsCorrectly(String apiCode, String expectedState) {
        OrderStatusMonitor.State state = OrderStatusMonitor.State.fromApiCode(apiCode);
        assertEquals(OrderStatusMonitor.State.valueOf(expectedState), state);
    }

    @Test
    void stateFromApiCode_nullInput_returnsUnknown() {
        assertEquals(OrderStatusMonitor.State.UNKNOWN,
                     OrderStatusMonitor.State.fromApiCode(null));
    }

    // ── OrderRequest builder ──────────────────────────────────────────────────

    @Test
    void orderRequestBuilder_marketOrder_producesCorrectMap() {
        Map<String, Object> params = new OrderRequest.Builder()
                .exchange(OrderRequest.Exchange.NSE)
                .tradingSymbol("RELIANCE-EQ")
                .transactionType(OrderRequest.TransactionType.BUY)
                .orderType(OrderRequest.OrderType.MARKET)
                .productType(OrderRequest.ProductType.MIS)
                .quantity(10)
                .validity(OrderRequest.Validity.DAY)
                .build()
                .toMap();

        assertEquals("NSE",         params.get("exchange"));
        assertEquals("RELIANCE-EQ", params.get("tradingSymbol"));
        assertEquals("BUY",         params.get("transactionType"));
        assertEquals("MKT",         params.get("orderType"));
        assertEquals("MIS",         params.get("productType"));
        assertEquals("10",          params.get("quantity"));
        assertEquals("DAY",         params.get("validity"));
    }

    @Test
    void orderRequestBuilder_limitOrderWithoutPrice_throwsIllegalState() {
        assertThrows(IllegalStateException.class, () ->
                new OrderRequest.Builder()
                        .exchange(OrderRequest.Exchange.NSE)
                        .tradingSymbol("INFY-EQ")
                        .transactionType(OrderRequest.TransactionType.SELL)
                        .orderType(OrderRequest.OrderType.LIMIT)
                        .productType(OrderRequest.ProductType.CNC)
                        .quantity(5)
                        .build()   // price not set → must throw
        );
    }

    @Test
    void orderRequestBuilder_zeroQuantity_throwsIllegalArgument() {
        assertThrows(IllegalArgumentException.class, () ->
                new OrderRequest.Builder()
                        .exchange(OrderRequest.Exchange.NSE)
                        .tradingSymbol("TCS-EQ")
                        .transactionType(OrderRequest.TransactionType.BUY)
                        .quantity(0)   // invalid
        );
    }

    @Test
    void orderRequestBuilder_tagExceeds20Chars_throwsIllegalArgument() {
        assertThrows(IllegalArgumentException.class, () ->
                new OrderRequest.Builder()
                        .tag("this-tag-is-way-too-long-for-the-api")
        );
    }
}
