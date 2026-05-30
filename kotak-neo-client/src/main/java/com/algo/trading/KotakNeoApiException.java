package com.algo.trading;

/**
 * Checked exception wrapping all Kotak Neo API failure modes.
 *
 * <p>Callers can catch this type to handle API-level failures (bad credentials,
 * rejected orders, throttling) separately from raw {@link java.io.IOException}
 * network failures.
 */
public class KotakNeoApiException extends Exception {

    public KotakNeoApiException(String message) {
        super(message);
    }

    public KotakNeoApiException(String message, Throwable cause) {
        super(message, cause);
    }
}
