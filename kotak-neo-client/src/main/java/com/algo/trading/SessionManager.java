package com.algo.trading;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ScheduledFuture;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * Keep-alive manager that silently re-authenticates the {@link KotakNeoClient}
 * on a configurable schedule (default: every 4 hours).
 *
 * <p>Kotak Neo JWT tokens are valid for roughly 8–12 hours, but idle sessions
 * can be revoked earlier. Refreshing every 4 hours is well within limits.
 *
 * <p>Usage:
 * <pre>{@code
 *   KotakNeoClient client = new KotakNeoClient(...);
 *   client.login();
 *
 *   SessionManager sm = new SessionManager(client);
 *   sm.start();                  // begins background refresh
 *   // ... do trading ...
 *   sm.stop();                   // clean shutdown
 *   client.close();
 * }</pre>
 */
public class SessionManager implements AutoCloseable {

    private static final Logger log = LoggerFactory.getLogger(SessionManager.class);

    /** Default refresh interval in hours. */
    private static final long DEFAULT_REFRESH_HOURS = 4;

    private final KotakNeoClient        client;
    private final long                  refreshIntervalHours;
    private final ScheduledExecutorService scheduler;
    private final AtomicBoolean         running = new AtomicBoolean(false);
    private       ScheduledFuture<?>    scheduledTask;

    // --------------------------------------------------------------------------
    // Constructors
    // --------------------------------------------------------------------------

    /**
     * Creates a manager with the default 4-hour refresh cadence.
     *
     * @param client an authenticated {@link KotakNeoClient} instance
     */
    public SessionManager(KotakNeoClient client) {
        this(client, DEFAULT_REFRESH_HOURS);
    }

    /**
     * Creates a manager with a custom refresh cadence.
     *
     * @param client               an authenticated {@link KotakNeoClient} instance
     * @param refreshIntervalHours hours between each silent re-login
     */
    public SessionManager(KotakNeoClient client, long refreshIntervalHours) {
        if (refreshIntervalHours < 1 || refreshIntervalHours > 12) {
            throw new IllegalArgumentException("refreshIntervalHours must be between 1 and 12");
        }
        this.client               = client;
        this.refreshIntervalHours = refreshIntervalHours;
        // Use a single daemon thread so it never blocks JVM shutdown
        this.scheduler = Executors.newSingleThreadScheduledExecutor(runnable -> {
            Thread t = new Thread(runnable, "kotak-session-refresh");
            t.setDaemon(true);
            return t;
        });
    }

    // --------------------------------------------------------------------------
    // Lifecycle
    // --------------------------------------------------------------------------

    /**
     * Starts the background refresh scheduler.
     * Has no effect if already running.
     */
    public synchronized void start() {
        if (running.compareAndSet(false, true)) {
            scheduledTask = scheduler.scheduleAtFixedRate(
                    this::refreshSession,
                    refreshIntervalHours,   // initial delay – first login was already done
                    refreshIntervalHours,
                    TimeUnit.HOURS
            );
            log.info("SessionManager started. Token refresh every {} hour(s).", refreshIntervalHours);
        }
    }

    /**
     * Stops the background scheduler gracefully.
     * Has no effect if not running.
     */
    public synchronized void stop() {
        if (running.compareAndSet(true, false)) {
            if (scheduledTask != null) {
                scheduledTask.cancel(false);
            }
            scheduler.shutdown();
            try {
                if (!scheduler.awaitTermination(5, TimeUnit.SECONDS)) {
                    scheduler.shutdownNow();
                }
            } catch (InterruptedException ex) {
                Thread.currentThread().interrupt();
                scheduler.shutdownNow();
            }
            log.info("SessionManager stopped.");
        }
    }

    /**
     * Returns {@code true} while the refresh scheduler is active.
     */
    public boolean isRunning() {
        return running.get();
    }

    // --------------------------------------------------------------------------
    // AutoCloseable
    // --------------------------------------------------------------------------

    @Override
    public void close() {
        stop();
    }

    // --------------------------------------------------------------------------
    // Internal
    // --------------------------------------------------------------------------

    private void refreshSession() {
        log.info("Scheduled token refresh: re-authenticating…");
        try {
            client.login();
            log.info("Token refreshed successfully.");
        } catch (KotakNeoApiException ex) {
            // Log the error but do not crash the scheduler thread.
            // The next scheduled tick will retry.
            log.error("Token refresh failed (will retry at next interval): {}", ex.getMessage());
        }
    }
}
