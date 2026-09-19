import { useState } from "react";
import { strings } from "../i18n";

/**
 * The Tool Selection Trace.
 *
 * Collapsed, it reads as a tape: one marker per model call, with the tool the
 * model picked and how long that call took. Expanded, every step shows what
 * the model could have chosen, what it said before choosing, the exact
 * arguments it passed, and what came back.
 */

const TOOL_LABELS = {
  get_current_weather: "current",
  get_forecast: "forecast",
  get_weather_alerts: "alerts",
  get_historical_weather: "historical",
  get_climate_trend: "climate",
};

const shortName = (tool) => TOOL_LABELS[tool] || tool;

function ToolCall({ call, t }) {
  return (
    <li className={`trace-call${call.ok ? "" : " is-failed"}`}>
      <div className="trace-call-head">
        <span className="tool-badge">{shortName(call.tool)}</span>
        <code className="trace-tool-name">{call.tool}</code>
        <span className="trace-duration">{call.duration_ms} ms</span>
      </div>

      <dl className="trace-fields">
        <dt>{t.input}</dt>
        <dd>
          <code>{JSON.stringify(call.input)}</code>
        </dd>
        <dt>{call.ok ? t.result : t.failed}</dt>
        <dd>
          <code>{call.ok ? call.result_preview : call.error}</code>
        </dd>
      </dl>
    </li>
  );
}

function Step({ step, t }) {
  const tools = step.tool_calls || [];
  const headline =
    step.decision === "use_tools"
      ? `${t.chose} ${tools.map((c) => shortName(c.tool)).join(", ")}`
      : step.decision === "stopped"
        ? t.stoppedEarly
        : t.answeredDirectly;

  return (
    <li className="trace-step">
      <div className="trace-step-head">
        <span className="trace-step-number">
          {t.step} {step.step}
        </span>
        <span className="trace-step-headline">{headline}</span>
        <span className="trace-duration">{step.model_latency_ms} ms</span>
      </div>

      <p className="trace-reason">
        {step.model_text ? (
          step.model_text
        ) : (
          <span className="trace-muted">{t.noReasonGiven}</span>
        )}
      </p>

      {tools.length > 0 && (
        <ul className="trace-calls">
          {tools.map((call) => (
            <ToolCall key={call.tool_use_id} call={call} t={t} />
          ))}
        </ul>
      )}

      <p className="trace-meta">
        {t.toolsAvailable}: {step.available_tools.map(shortName).join(" · ")}
        {step.input_tokens != null && (
          <>
            {" — "}
            {step.input_tokens + (step.output_tokens || 0)} {t.tokens}
          </>
        )}
      </p>
    </li>
  );
}

export default function TraceTape({ trace, language }) {
  const [open, setOpen] = useState(false);
  const t = strings(language);

  if (!trace?.steps?.length) return null;

  const picked = trace.steps.flatMap((step) =>
    (step.tool_calls || []).map((call) => call.tool)
  );

  return (
    <div className={`trace${open ? " is-open" : ""}`}>
      <button
        type="button"
        className="trace-toggle"
        onClick={() => setOpen((wasOpen) => !wasOpen)}
        aria-expanded={open}
      >
        <span className="trace-rail" aria-hidden="true">
          {trace.steps.map((step) => (
            <span
              key={step.step}
              className={`trace-tick is-${step.decision.replace("_", "-")}`}
            />
          ))}
        </span>

        <span className="trace-toggle-text">
          {picked.length > 0
            ? picked.map(shortName).join(" → ")
            : t.answeredDirectly}
        </span>

        <span className="trace-duration">{trace.total_ms} ms</span>
        <span className="trace-toggle-label">
          {open ? t.hideDecision : t.howItDecided}
        </span>
      </button>

      {open && (
        <div className="trace-body">
          <ol className="trace-steps">
            {trace.steps.map((step) => (
              <Step key={step.step} step={step} t={t} />
            ))}
          </ol>
          <p className="trace-footer">
            <code>{trace.model}</code> — {t.total} {trace.total_ms} ms
          </p>
        </div>
      )}
    </div>
  );
}
