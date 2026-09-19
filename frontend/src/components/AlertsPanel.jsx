import { strings } from "../i18n";

export default function AlertsPanel({
  language,
  alerts,
  onDismiss,
  onRefresh,
  refreshing,
  lastRunAt,
}) {
  const t = strings(language);

  return (
    <section className="panel">
      <div className="panel-head">
        <h2 className="panel-title">{t.alerts}</h2>
        <button
          type="button"
          className="link-button"
          onClick={onRefresh}
          disabled={refreshing}
        >
          {refreshing ? t.checking : t.checkNow}
        </button>
      </div>

      {alerts.length === 0 ? (
        <p className="panel-empty">{t.noAlerts}</p>
      ) : (
        <ul className="alert-list">
          {alerts.map((alert) => (
            <li key={alert.id} className={`alert is-${alert.severity}`}>
              <div className="alert-head">
                <span className="alert-severity">{alert.severity_label}</span>
                <span className="alert-place">{alert.location_label}</span>
              </div>
              <p className="alert-headline">{alert.headline}</p>
              <p className="alert-advice">{alert.advice}</p>
              <button
                type="button"
                className="link-button"
                onClick={() => onDismiss(alert.id)}
              >
                {t.dismiss}
              </button>
            </li>
          ))}
        </ul>
      )}

      {lastRunAt && (
        <p className="panel-foot">
          <time dateTime={lastRunAt}>{new Date(lastRunAt).toLocaleTimeString()}</time>
        </p>
      )}
    </section>
  );
}
