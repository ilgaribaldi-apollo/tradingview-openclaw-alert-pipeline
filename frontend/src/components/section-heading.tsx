export function SectionHeading({
  eyebrow,
  title,
  body,
}: {
  eyebrow: string;
  title: string;
  body: string;
}) {
  return (
    <div>
      <p className="text-[11px] uppercase tracking-[0.35em] text-cyan-300/70">{eyebrow}</p>
      <h2 className="mt-3 text-3xl font-semibold tracking-tight text-white sm:text-4xl">{title}</h2>
      <p className="mt-3 max-w-3xl text-sm leading-7 text-zinc-400 sm:text-base">{body}</p>
    </div>
  );
}
