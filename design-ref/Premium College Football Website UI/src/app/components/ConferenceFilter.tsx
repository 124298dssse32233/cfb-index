interface ConferenceFilterProps {
  selected: string;
  onChange: (conference: string) => void;
}

const conferences = ['All', 'SEC', 'Big Ten', 'Big 12', 'ACC', 'Pac-12', 'Group of 5'];

export function ConferenceFilter({ selected, onChange }: ConferenceFilterProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {conferences.map((conf) => (
        <button
          key={conf}
          onClick={() => onChange(conf)}
          className={`px-4 py-2 rounded-full transition-all ${
            selected === conf
              ? 'bg-[var(--accent)] text-[var(--accent-foreground)] shadow-sm'
              : 'bg-[var(--secondary)] text-[var(--foreground)] hover:bg-[var(--muted)]'
          }`}
        >
          {conf}
        </button>
      ))}
    </div>
  );
}
