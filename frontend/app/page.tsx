import Link from "next/link";

const STEPS = [
  {
    number: 1,
    title: "Import a dataset",
    description: "Fetch daily OHLCV bars directly from Yahoo Finance by ticker.",
    href: "/datasets/import",
    linkLabel: "Import a dataset",
  },
  {
    number: 2,
    title: "Create a strategy",
    description: "Define an SMA crossover specification with your chosen windows.",
    href: "/strategies/new",
    linkLabel: "Create a strategy",
  },
  {
    number: 3,
    title: "Create and run a backtest",
    description: "Pick your strategy, dataset, and period, then execute it.",
    href: "/runs/new",
    linkLabel: "Create a run",
  },
  {
    number: 4,
    title: "Or search parameters",
    description: "Run a chronological train/validation/holdout optimization instead.",
    href: "/optimizations/new",
    linkLabel: "Create an optimization",
  },
] as const;

const EXPLORE_LINKS = [
  { href: "/datasets", label: "Datasets" },
  { href: "/runs", label: "Runs" },
  { href: "/strategies", label: "Strategies" },
  { href: "/optimizations", label: "Optimizations" },
  { href: "/system", label: "System status" },
] as const;

export default function LandingPage() {
  return (
    <>
      <h1>IDX Backtesting Lab</h1>
      <p className="hero-disclaimer">
        Local-first research tooling for transparent, reproducible backtests of Indonesia Stock
        Exchange (IDX) equities. Historical simulations are research artifacts, not investment
        advice and not a prediction of future performance.
      </p>

      <section aria-labelledby="getting-started-heading">
        <h2 id="getting-started-heading">Getting started</h2>
        <div className="step-grid">
          {STEPS.map((step) => (
            <div className="step-card" key={step.href}>
              <span className="step-number" aria-hidden="true">
                {step.number}
              </span>
              <h3>{step.title}</h3>
              <p>{step.description}</p>
              <Link href={step.href}>{step.linkLabel} →</Link>
            </div>
          ))}
        </div>
      </section>

      <section aria-labelledby="explore-heading">
        <h2 id="explore-heading">Already have data?</h2>
        <div className="link-grid">
          {EXPLORE_LINKS.map((link) => (
            <Link href={link.href} key={link.href}>
              {link.label}
            </Link>
          ))}
        </div>
      </section>
    </>
  );
}
