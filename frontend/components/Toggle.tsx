interface Props {
  checked: boolean;
  onChange: (value: boolean) => void;
  label: string;
}

export default function Toggle({ checked, onChange, label }: Props) {
  return (
    <label className="toggle" aria-label={label}>
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <span className="toggle-track" />
      <span className="toggle-thumb" />
    </label>
  );
}
