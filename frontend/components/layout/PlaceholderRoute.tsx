export function PlaceholderRoute({
  title,
  description,
  ownedBy,
}: {
  title: string;
  description: string;
  ownedBy: string;
}) {
  return (
    <>
      <h1>{title}</h1>
      <p>{description}</p>
      <p>This workflow is implemented in {ownedBy}. No controls exist here yet.</p>
    </>
  );
}
