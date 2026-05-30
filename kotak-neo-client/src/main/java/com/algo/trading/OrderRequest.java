package com.algo.trading;

import java.util.HashMap;
import java.util.Map;
import java.util.Objects;

/**
 * Immutable, type-safe representation of a Kotak Neo order.
 *
 * <p>Use the {@link Builder} to construct validated order maps:
 * <pre>{@code
 *   Map<String, Object> params = new OrderRequest.Builder()
 *       .exchange("NSE")
 *       .tradingSymbol("RELIANCE-EQ")
 *       .transactionType(OrderRequest.TransactionType.BUY)
 *       .orderType(OrderRequest.OrderType.MARKET)
 *       .productType(OrderRequest.ProductType.MIS)
 *       .quantity(10)
 *       .validity(OrderRequest.Validity.DAY)
 *       .build()
 *       .toMap();
 * }</pre>
 */
public final class OrderRequest {

    // --------------------------------------------------------------------------
    // Enumerations for valid field values
    // --------------------------------------------------------------------------

    public enum TransactionType { BUY, SELL }

    public enum Exchange { NSE, BSE, NFO, BFO, CDS, MCX }

    public enum OrderType {
        MARKET("MKT"),
        LIMIT("L"),
        STOP_LOSS("SL"),
        STOP_LOSS_MARKET("SL-M");

        private final String apiCode;
        OrderType(String apiCode) { this.apiCode = apiCode; }
        public String apiCode()   { return apiCode; }
    }

    public enum ProductType {
        /** Intraday margin trading */
        MIS,
        /** Delivery (CNC) */
        CNC,
        /** Normal carry-forward */
        NRML
    }

    public enum Validity {
        /** Good-till-day (expires at market close) */
        DAY,
        /** Immediate-or-cancel */
        IOC
    }

    // --------------------------------------------------------------------------
    // Fields
    // --------------------------------------------------------------------------

    private final Exchange         exchange;
    private final String           tradingSymbol;
    private final TransactionType  transactionType;
    private final OrderType        orderType;
    private final ProductType      productType;
    private final int              quantity;
    private final double           price;       // 0 for MARKET orders
    private final double           triggerPrice;// for SL/SL-M orders
    private final Validity         validity;
    private final String           tag;         // optional client-side correlation tag

    private OrderRequest(Builder builder) {
        this.exchange        = builder.exchange;
        this.tradingSymbol   = builder.tradingSymbol;
        this.transactionType = builder.transactionType;
        this.orderType       = builder.orderType;
        this.productType     = builder.productType;
        this.quantity        = builder.quantity;
        this.price           = builder.price;
        this.triggerPrice    = builder.triggerPrice;
        this.validity        = builder.validity;
        this.tag             = builder.tag;
    }

    /**
     * Serializes this order into the key-value map expected by
     * {@link KotakNeoClient#placeOrder(Map)}.
     */
    public Map<String, Object> toMap() {
        Map<String, Object> map = new HashMap<>();
        map.put("exchange",         exchange.name());
        map.put("tradingSymbol",    tradingSymbol);
        map.put("transactionType",  transactionType.name());
        map.put("orderType",        orderType.apiCode());
        map.put("productType",      productType.name());
        map.put("quantity",         String.valueOf(quantity));
        map.put("price",            String.valueOf(price));
        map.put("triggerPrice",     String.valueOf(triggerPrice));
        map.put("validity",         validity.name());
        if (tag != null && !tag.isBlank()) {
            map.put("tag", tag);
        }
        return map;
    }

    // --------------------------------------------------------------------------
    // Builder
    // --------------------------------------------------------------------------

    public static final class Builder {

        private Exchange        exchange;
        private String          tradingSymbol;
        private TransactionType transactionType;
        private OrderType       orderType       = OrderType.MARKET;
        private ProductType     productType     = ProductType.MIS;
        private int             quantity;
        private double          price           = 0.0;
        private double          triggerPrice    = 0.0;
        private Validity        validity        = Validity.DAY;
        private String          tag;

        public Builder exchange(Exchange exchange) {
            this.exchange = Objects.requireNonNull(exchange);
            return this;
        }

        public Builder exchange(String exchange) {
            this.exchange = Exchange.valueOf(exchange.toUpperCase());
            return this;
        }

        public Builder tradingSymbol(String tradingSymbol) {
            this.tradingSymbol = Objects.requireNonNull(tradingSymbol, "tradingSymbol required");
            return this;
        }

        public Builder transactionType(TransactionType transactionType) {
            this.transactionType = Objects.requireNonNull(transactionType);
            return this;
        }

        public Builder orderType(OrderType orderType) {
            this.orderType = Objects.requireNonNull(orderType);
            return this;
        }

        public Builder productType(ProductType productType) {
            this.productType = Objects.requireNonNull(productType);
            return this;
        }

        public Builder quantity(int quantity) {
            if (quantity <= 0) throw new IllegalArgumentException("quantity must be > 0");
            this.quantity = quantity;
            return this;
        }

        public Builder price(double price) {
            if (price < 0) throw new IllegalArgumentException("price must be >= 0");
            this.price = price;
            return this;
        }

        public Builder triggerPrice(double triggerPrice) {
            if (triggerPrice < 0) throw new IllegalArgumentException("triggerPrice must be >= 0");
            this.triggerPrice = triggerPrice;
            return this;
        }

        public Builder validity(Validity validity) {
            this.validity = Objects.requireNonNull(validity);
            return this;
        }

        /** Optional correlation tag visible in your order book. Max 20 chars. */
        public Builder tag(String tag) {
            if (tag != null && tag.length() > 20) {
                throw new IllegalArgumentException("tag must be <= 20 characters");
            }
            this.tag = tag;
            return this;
        }

        /**
         * Validates all mandatory fields and builds the {@link OrderRequest}.
         *
         * @throws IllegalStateException if any mandatory field is missing
         */
        public OrderRequest build() {
            Objects.requireNonNull(exchange,        "exchange is required");
            Objects.requireNonNull(tradingSymbol,   "tradingSymbol is required");
            Objects.requireNonNull(transactionType, "transactionType is required");
            if (quantity <= 0) {
                throw new IllegalStateException("quantity must be set and > 0");
            }
            if (orderType == OrderType.LIMIT && price <= 0) {
                throw new IllegalStateException("price must be > 0 for LIMIT orders");
            }
            if ((orderType == OrderType.STOP_LOSS || orderType == OrderType.STOP_LOSS_MARKET)
                    && triggerPrice <= 0) {
                throw new IllegalStateException("triggerPrice must be > 0 for SL/SL-M orders");
            }
            return new OrderRequest(this);
        }
    }
}
