interface Props {
  size?: number;
}

export default function AssistantAvatarIcon({ size = 32 }: Props) {
  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: "50%",
        flexShrink: 0,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "#0f172a",
        color: "var(--accent-soft)",
      }}
    >
      <svg
        width={size * 0.6}
        height={size * 0.6}
        viewBox="0 0 24 24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <rect x="5" y="8" width="14" height="11" rx="3" stroke="currentColor" strokeWidth="1.6" />
        <line x1="12" y1="8" x2="12" y2="4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
        <circle cx="12" cy="3" r="1.3" fill="currentColor" />
        <circle cx="9.5" cy="13" r="1.3" fill="currentColor" />
        <circle cx="14.5" cy="13" r="1.3" fill="currentColor" />
        <line x1="9" y1="17" x2="15" y2="17" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
        <line x1="2" y1="12" x2="5" y2="12" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
        <line x1="19" y1="12" x2="22" y2="12" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      </svg>
    </div>
  );
}
