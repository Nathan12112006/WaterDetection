interface DetectionSummaryProps {
  items: readonly string[]
}

export function DetectionSummary({ items }: DetectionSummaryProps) {
  return (
    <section id="results" className="panel results">
      <div className="results-heading">
        <div>
          <p className="section-kicker">Run output</p>
          <h2>Detection summary</h2>
        </div>
      </div>
      <ul id="detection-list">
        {items.map((item, index) => (
          <li key={`${index}-${item}`}>{item}</li>
        ))}
      </ul>
    </section>
  )
}
