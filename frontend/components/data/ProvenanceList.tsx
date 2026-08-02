export interface ProvenanceItem {
  label: string;
  value: string | null;
}

export function ProvenanceList({ items }: { items: ProvenanceItem[] }) {
  return (
    <dl>
      {items.map((item) => (
        <div key={item.label}>
          <dt>{item.label}</dt>
          <dd className="id-value">{item.value ?? "Not provided"}</dd>
        </div>
      ))}
    </dl>
  );
}
