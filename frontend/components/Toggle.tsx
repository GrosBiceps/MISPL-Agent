interface Props {
  checked: boolean;
  onChange: (value: boolean) => void;
  label: string;
  disabled?: boolean;
}

export default function Toggle({ checked, onChange, label, disabled = false }: Props) {
  return (
    <label className={`toggle${disabled ? " toggle-disabled" : ""}`}>
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        aria-label={label}
        disabled={disabled}
      />
      <span className="toggle-track" />
      <span className="toggle-thumb" />
    </label>
  );
}
