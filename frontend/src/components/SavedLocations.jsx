import { useState } from "react";
import { strings } from "../i18n";

export default function SavedLocations({ language, locations, onAdd, onRemove, error }) {
  const t = strings(language);
  const [value, setValue] = useState("");
  const [saving, setSaving] = useState(false);

  const add = async () => {
    const place = value.trim();
    if (!place || saving) return;
    setSaving(true);
    const ok = await onAdd(place);
    setSaving(false);
    if (ok) setValue("");
  };

  return (
    <section className="panel">
      <h2 className="panel-title">{t.savedPlaces}</h2>

      {locations.length === 0 ? (
        <p className="panel-empty">{t.noPlaces}</p>
      ) : (
        <ul className="place-list">
          {locations.map((place) => (
            <li key={place.id} className="place">
              <span className="place-name">
                {place.name}
                {place.region && <span className="place-region">{place.region}</span>}
              </span>
              <button
                type="button"
                className="link-button"
                onClick={() => onRemove(place.id)}
                aria-label={`${t.remove} ${place.name}`}
              >
                {t.remove}
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className="place-add">
        <input
          className="place-input"
          value={value}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={(event) => event.key === "Enter" && add()}
          placeholder={t.addPlacePlaceholder}
          aria-label={t.addPlace}
        />
        <button type="button" className="button-quiet" onClick={add} disabled={saving}>
          {t.save}
        </button>
      </div>

      {error && <p className="panel-error">{error}</p>}
    </section>
  );
}
