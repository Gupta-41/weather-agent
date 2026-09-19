import { strings } from "../i18n";

export default function LanguagePicker({ languages, value, onChange, language }) {
  const t = strings(language);

  return (
    <label className="language-picker">
      <span className="visually-hidden">{t.language}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {languages.map((item) => (
          <option key={item.code} value={item.code}>
            {item.native}
          </option>
        ))}
      </select>
    </label>
  );
}
