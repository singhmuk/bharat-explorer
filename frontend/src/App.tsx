import { useEffect, useState, FormEvent } from "react";
import {
  Link,
  Route,
  Routes,
  useNavigate,
  useParams,
} from "react-router-dom";
import ReactMarkdown from "react-markdown";
import { api, auth, Dest, Rec } from "./api";
import AdSlot from "./AdSlot";

const REGIONS = [
  "North",
  "South",
  "East",
  "West",
  "Central",
  "Northeast",
];

function Header() {
  const nav = useNavigate();
  const [signedIn, setSignedIn] = useState(Boolean(auth.token));

  const signOut = () => {
    auth.clear();
    setSignedIn(false);
    nav("/");
  };

  return (
    <header className="top">
      <Link to="/" className="brand">
        Bharat Explorer
      </Link>

      <nav>
        <Link to="/">Places</Link>

        {signedIn && auth.token ? (
          <>
            <Link to="/dashboard">My trips</Link>
            <button className="link" onClick={signOut}>
              Sign out
            </button>
          </>
        ) : (
          <Link to="/login" className="btn small">
            Sign in
          </Link>
        )}
      </nav>
    </header>
  );
}

function Home() {
  const [items, setItems] = useState<Dest[]>([]);
  const [region, setRegion] = useState("");
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    let active = true;
    const params = new URLSearchParams();

    if (region) params.set("region", region);
    if (q.trim()) params.set("q", q.trim());

    setLoading(true);
    setErr("");

    api<Dest[]>(`/destinations?${params.toString()}`)
      .then((data) => {
        if (active) setItems(data);
      })
      .catch((error: Error) => {
        if (active) {
          setItems([]);
          setErr(error.message);
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [region, q]);

  return (
    <main>
      <section className="hero">
        <h1>
          From the Thar to the Sundarbans, find the India that fits you
        </h1>

        <p>
          Discover destinations, explore travel guides, and plan your next
          Indian adventure.
        </p>

        <input
          type="search"
          placeholder="Search a place, for example Hampi"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          aria-label="Search destinations"
        />

        <div className="chips">
          <button
            className={!region ? "on" : ""}
            onClick={() => setRegion("")}
          >
            All India
          </button>

          {REGIONS.map((r) => (
            <button
              key={r}
              className={region === r ? "on" : ""}
              onClick={() => setRegion(r)}
            >
              {r}
            </button>
          ))}
        </div>
      </section>

      {err && (
        <p className="error" role="alert">
          {err}
        </p>
      )}

      <section className="grid">
        {loading ? (
          <p className="empty">Loading destinations...</p>
        ) : (
          <>
            {items.map((d) => (
              <Link
                key={d.id}
                to={`/place/${d.slug}`}
                className="card"
              >
                {d.image_url && (
                  <img
                    src={d.image_url}
                    alt={d.image_alt || d.name}
                    loading="lazy"
                    className="destination-card-image"
                  />
                )}

                <h3>{d.name}</h3>

                <span className="state">
                  {d.state} · {d.region}
                </span>

                <p>{d.summary}</p>

                {d.best_season && (
                  <p>
                    <strong>Best season:</strong> {d.best_season}
                  </p>
                )}

                <div className="tags">
                  {(d.tags || []).map((tag) => (
                    <i key={tag}>{tag}</i>
                  ))}
                </div>

                {typeof d.popularity === "number" && (
                  <small>Popularity: {d.popularity}</small>
                )}
              </Link>
            ))}

            {!items.length && !err && (
              <p className="empty">
                No destinations match. Clear the search or choose another
                region.
              </p>
            )}
          </>
        )}
      </section>

      <AdSlot slot="1111111111" />
    </main>
  );
}

function Place() {
  const { slug } = useParams<{ slug: string }>();

  const [d, setD] = useState<Dest | null>(null);
  const [msg, setMsg] = useState("");
  const [loading, setLoading] = useState(true);
  const [actionBusy, setActionBusy] = useState(false);

  useEffect(() => {
    let active = true;

    setD(null);
    setMsg("");
    setLoading(true);

    if (!slug) {
      setMsg("Destination slug is missing.");
      setLoading(false);
      return;
    }

    api<Dest>(`/destinations/${encodeURIComponent(slug)}`)
      .then((data) => {
        if (active) setD(data);
      })
      .catch((error: Error) => {
        if (active) setMsg(error.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    if (auth.token) {
      api("/visits", {
        method: "POST",
        body: JSON.stringify({ slug, action: "view" }),
      }).catch(() => { });
    }

    return () => {
      active = false;
    };
  }, [slug]);

  const act = async () => {
    if (!auth.token) {
      setMsg("Please sign in to save this destination.");
      return;
    }

    setActionBusy(true);
    setMsg("");

    try {
      await api("/visits", {
        method: "POST",
        body: JSON.stringify({ slug, action: "save" }),
      });

      setMsg("Destination saved. Your recommendations can now improve.");
    } catch (error) {
      setMsg((error as Error).message);
    } finally {
      setActionBusy(false);
    }
  };

  const book = async () => {
    if (!auth.token) {
      setMsg("Please sign in to access accommodation links.");
      return;
    }

    setActionBusy(true);
    setMsg("");

    try {
      const { url } = await api<{ url: string }>(
        `/go/${encodeURIComponent(slug || "")}`
      );

      if (!url) {
        throw new Error("No accommodation link is available.");
      }

      const parsedUrl = new URL(url);

      if (!["http:", "https:"].includes(parsedUrl.protocol)) {
        throw new Error("The accommodation link is invalid.");
      }

      window.open(parsedUrl.href, "_blank", "noopener,noreferrer");
    } catch (error) {
      setMsg((error as Error).message);
    } finally {
      setActionBusy(false);
    }
  };

  if (loading) {
    return (
      <main className="place">
        <p className="empty">Loading destination details...</p>
      </main>
    );
  }

  if (!d) {
    return (
      <main className="place">
        <h1>Destination unavailable</h1>
        <p className="error" role="alert">
          {msg || "We could not find this destination."}
        </p>
        <Link to="/" className="btn">
          Browse destinations
        </Link>
      </main>
    );
  }

  const mapUrl = `https://www.google.com/maps?q=${d.lat},${d.lng}`;

  const details: { label: string; value: React.ReactNode }[] = [
    { label: "Name", value: d.name },
    { label: "State", value: d.state },
    { label: "Region", value: d.region },
    {
      label: "Best season to visit",
      value: d.best_season || "Not specified",
    },
    {
      label: "Popularity score",
      value:
        typeof d.popularity === "number"
          ? d.popularity
          : "Not available",
    },
    {
      label: "Map",
      value: (
        <a href={mapUrl} target="_blank" rel="noreferrer">
          Open {d.name} in Google Maps
        </a>
      ),
    },
    ...(d.updated_at
      ? [
        {
          label: "Last updated",
          value: Number.isNaN(Date.parse(d.updated_at))
            ? d.updated_at
            : new Date(d.updated_at).toLocaleDateString(),
        },
      ]
      : []),
    {
      label: "Tags",
      value: d.tags?.length ? d.tags.join(", ") : "Not specified",
    },
    {
      label: "Affiliate link",
      value: d.affiliate_url ? (
        <a
          href={d.affiliate_url}
          target="_blank"
          rel="sponsored noreferrer"
        >
          View accommodation options
        </a>
      ) : (
        "Not available"
      ),
    },
  ];

  return (
    <main className="place">
      <nav aria-label="Breadcrumb" className="breadcrumbs">
        <Link to="/">Places</Link>
        <span> / </span>
        <span>{d.name}</span>
      </nav>

      <p className="state">
        {d.state} · {d.region} India
      </p>

      <h1>{d.name}</h1>

      {d.summary && <p className="lead">{d.summary}</p>}

      {d.image_url && (
        <figure className="destination-image">
          <img
            src={d.image_url}
            alt={d.image_alt || `${d.name}, ${d.state}, India`}
            loading="eager"
          />
          {d.image_alt && <figcaption>{d.image_alt}</figcaption>}
        </figure>
      )}

      {d.description && (
        <section>
          <h2>About {d.name}</h2>
          <p>{d.description}</p>
        </section>
      )}

      {d.tags?.length > 0 && (
        <section>
          <h2>What to explore</h2>
          <div className="tags">
            {d.tags.map((tag) => (
              <i key={tag}>{tag}</i>
            ))}
          </div>
        </section>
      )}

      <div className="row">
        <button className="btn" onClick={book} disabled={actionBusy}>
          Find stays
        </button>

        <button
          className="btn ghost"
          onClick={act}
          disabled={actionBusy}
        >
          Save place
        </button>
      </div>

      {msg && (
        <p className="note" role="status">
          {msg}
        </p>
      )}

      <section className="destination-details">
        <h2>Destination information</h2>

        <dl className="destination-details-list">
          {details.map((item) => (
            <div className="detail-row" key={item.label}>
              <dt>{item.label}</dt>
              <dd>{item.value}</dd>
            </div>
          ))}
        </dl>
      </section>

      {d.guide_md?.trim() && (
        <article className="city-guide">
          <h2>Travel guide to {d.name}</h2>
          <ReactMarkdown>{d.guide_md}</ReactMarkdown>
        </article>
      )}

      {(d.meta_title || d.meta_description) && (
        <section className="seo-details">
          <h2>SEO information</h2>

          {d.meta_title && (
            <p>
              <strong>Meta title:</strong> {d.meta_title}
            </p>
          )}

          {d.meta_description && (
            <p>
              <strong>Meta description:</strong> {d.meta_description}
            </p>
          )}
        </section>
      )}

      <p className="disclosure">
        Stay links are affiliate links. We may earn a commission at no
        additional cost to you.
      </p>

      <AdSlot slot="2222222222" />
    </main>
  );
}

function Login() {
  const nav = useNavigate();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setErr("");
    setBusy(true);

    const form = new FormData(e.currentTarget);

    try {
      const result = await api<{ access_token: string }>(
        `/auth/${mode}`,
        {
          method: "POST",
          body: JSON.stringify({
            email: form.get("email"),
            password: form.get("password"),
          }),
        }
      );

      auth.set(result.access_token);
      nav("/dashboard");
    } catch (error) {
      setErr((error as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="narrow">
      <h1>{mode === "login" ? "Sign in" : "Create your account"}</h1>

      <form onSubmit={submit}>
        <label>
          Email
          <input name="email" type="email" autoComplete="email" required />
        </label>

        <label>
          Password (8+ characters)
          <input
            name="password"
            type="password"
            minLength={8}
            autoComplete={
              mode === "login" ? "current-password" : "new-password"
            }
            required
          />
        </label>

        <button className="btn" disabled={busy}>
          {busy
            ? "Please wait..."
            : mode === "login"
              ? "Sign in"
              : "Create account"}
        </button>
      </form>

      {err && (
        <p className="error" role="alert">
          {err}
        </p>
      )}

      <button
        className="link"
        onClick={() => {
          setMode(mode === "login" ? "register" : "login");
          setErr("");
        }}
      >
        {mode === "login"
          ? "New here? Create an account"
          : "Have an account? Sign in"}
      </button>
    </main>
  );
}

function Dashboard() {
  const nav = useNavigate();

  const [recs, setRecs] = useState<Rec[]>([]);
  const [prompt, setPrompt] = useState("");
  const [days, setDays] = useState(5);
  const [plan, setPlan] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (!auth.token) {
      nav("/login");
      return;
    }

    let active = true;

    api<Rec[]>("/recommendations")
      .then((data) => {
        if (active) setRecs(data);
      })
      .catch((error: Error) => {
        if (active) setErr(error.message);
      });

    return () => {
      active = false;
    };
  }, [nav]);

  const generate = async () => {
    if (prompt.trim().length < 10) {
      setErr("Please describe your trip in at least 10 characters.");
      return;
    }

    setBusy(true);
    setErr("");
    setPlan("");

    try {
      const { task_id } = await api<{ task_id: string }>(
        "/ai/itinerary",
        {
          method: "POST",
          body: JSON.stringify({
            prompt: prompt.trim(),
            days,
          }),
        }
      );

      let completed = false;

      for (let i = 0; i < 60; i++) {
        await new Promise((resolve) => setTimeout(resolve, 2000));

        const result = await api<{
          status: string;
          text?: string;
        }>(`/ai/itinerary/${encodeURIComponent(task_id)}`);

        if (result.status === "done") {
          setPlan(result.text || "The itinerary was empty.");
          completed = true;
          break;
        }

        if (result.status === "failed") {
          throw new Error("We couldn't build that plan. Please try again.");
        }
      }

      if (!completed) {
        throw new Error("Planning is taking too long. Please try again.");
      }
    } catch (error) {
      setErr((error as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <main>
      <h1>Picked for you</h1>

      {err && (
        <p className="error" role="alert">
          {err}
        </p>
      )}

      <section className="grid">
        {recs.map((r) => (
          <Link key={r.slug} to={`/place/${r.slug}`} className="card">
            <h3>{r.name}</h3>
            <span className="state">{r.state}</span>
            <p>{r.summary}</p>
            <p className="why">{r.reason}</p>
          </Link>
        ))}

        {!recs.length && (
          <p className="empty">
            Open a few places and save the ones you like. Your
            recommendations will appear here.
          </p>
        )}
      </section>

      <section className="planner">
        <h2>Plan a trip with AI</h2>

        <textarea
          rows={3}
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Example: A relaxed trip with my parents in December, temples and good food, no long drives"
        />

        <div className="row">
          <label>
            Days
            <input
              type="number"
              min={1}
              max={14}
              value={days}
              onChange={(e) => {
                const value = Number(e.target.value);
                setDays(Math.max(1, Math.min(14, value || 1)));
              }}
            />
          </label>

          <button
            className="btn"
            disabled={busy || prompt.trim().length < 10}
            onClick={generate}
          >
            {busy ? "Planning your trip..." : "Build itinerary"}
          </button>
        </div>

        {plan && (
          <article className="plan">
            <ReactMarkdown>{plan}</ReactMarkdown>
          </article>
        )}
      </section>
    </main>
  );
}

export default function App() {
  return (
    <>
      <Header />

      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/place/:slug" element={<Place />} />
        <Route path="/login" element={<Login />} />
        <Route path="/dashboard" element={<Dashboard />} />
      </Routes>
    </>
  );
}