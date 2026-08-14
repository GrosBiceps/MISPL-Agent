interface Props {
  initials: string;
  size?: number;
}

export default function UserAvatarBadge({ initials, size = 32 }: Props) {
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
        background: "var(--accent-solid)",
        color: "var(--accent-solid-text)",
        fontFamily: "var(--sans)",
        fontSize: 13,
        fontWeight: 600,
      }}
    >
      {initials}
    </div>
  );
}
