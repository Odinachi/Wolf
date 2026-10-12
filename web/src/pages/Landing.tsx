import { ArrowRight, Code2, Github, MessageSquareText, MoreHorizontal, MousePointerClick, Smartphone, Trash2 } from 'lucide-react';
import { useCallback, useEffect, useState, type UIEvent } from 'react';
import { Link, useNavigate } from 'react-router';
import { AuthModal } from '../components/AuthModal';
import { BuildDemo } from '../components/BuildDemo';
import { Logo } from '../components/Logo';
import { PromptBox } from '../components/PromptBox';
import { PromptMarquee } from '../components/PromptMarquee';
import { Reveal } from '../components/Reveal';
import { RotatingWord } from '../components/RotatingWord';
import { Spotlight } from '../components/Spotlight';
import { UserMenu } from '../components/UserMenu';
import { WaveBackground } from '../components/WaveBackground';
import { EXAMPLES, PROMPT_IDEAS } from '../examples';
import { api, type ProjectSummary } from '../lib/api';
import { useAuth } from '../lib/auth';
import { timeAgo } from '../lib/time';
import { useMediaQuery } from '../lib/useMediaQuery';
import { PhoneThumbnail } from '../renderer/PhoneFrame';

const GITHUB_URL = 'https://github.com/Odinachi/Wolf';
const PENDING_KEY = 'wolf:pending-prompt';
// Set while the user is away signing in, so the pending prompt is built when they come back.
const RESUME_KEY = 'wolf:resume-build';
const APP_KINDS = ['mobile', 'fitness', 'recipe', 'shopping', 'travel', 'habit'];
const MARQUEE_ROWS = [
  PROMPT_IDEAS,
  [
    'A meditation app with breathing exercises',
    'A book club app with reading goals',
    'A parking app that finds open spots',
    'A study planner with Pomodoro timers',
    'A pet adoption app for local shelters',
    'A travel journal with maps and photos',
  ],
];

export function Landing() {
  const { user, loading } = useAuth();
  const navigate = useNavigate();
  const [prompt, setPrompt] = useState(() => sessionStorage.getItem(PENDING_KEY) ?? '');
  const [auth, setAuth] = useState<{ open: boolean; reason?: string }>({ open: false });
  const [authError, setAuthError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [projects, setProjects] = useState<ProjectSummary[] | null>(null);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  useEffect(() => {
    if (!user) { setProjects(null); return; }
    api.projects().then(setProjects).catch(() => setProjects([]));
  }, [user]);

  // Back from the provider with an error: show it once and clean the URL.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const err = params.get('auth_error');
    if (err) {
      setAuthError(err);
      sessionStorage.removeItem(RESUME_KEY);
      window.history.replaceState(null, '', window.location.pathname);
    }
  }, []);

  const build = useCallback(async (text: string) => {
    setError(null);
    setCreating(true);
    try {
      const project = await api.createProject(text);
      sessionStorage.removeItem(PENDING_KEY);
      navigate(`/p/${project.id}`, { state: { autostart: text } });
    } catch (e) {
      setError((e as Error).message);
      setCreating(false);
    }
  }, [navigate]);

  // Back from signing in with a prompt waiting: build it.
  useEffect(() => {
    if (!user || !sessionStorage.getItem(RESUME_KEY)) return;
    sessionStorage.removeItem(RESUME_KEY);
    const pending = sessionStorage.getItem(PENDING_KEY);
    if (pending) build(pending);
  }, [user, build]);

  const submit = () => {
    const text = prompt.trim();
    if (!text) return;
    if (!user) {
      // Keep the prompt across the trip to GitHub/Google so nothing typed is lost.
      sessionStorage.setItem(PENDING_KEY, text);
      setAuth({ open: true, reason: 'Sign in with GitHub or Google and Wolf will start building your app right away.' });
      return;
    }
    build(text);
  };

  const removeProject = async (id: string) => {
    if (!confirm('Delete this app? This can’t be undone.')) return;
    await api.deleteProject(id);
    setProjects(p => p?.filter(x => x.id !== id) ?? null);
  };

  return (
    <div className="min-h-dvh bg-[#FCFCFD] text-zinc-950">
      {/* Nav */}
      <header className={`fixed inset-x-0 top-0 z-30 transition-[background,box-shadow] duration-300 ${scrolled ? 'bg-white/75 shadow-[0_1px_0_rgb(24_24_27/0.06)] backdrop-blur-xl' : ''}`}>
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-5">
          <Link to="/" aria-label="Wolf home"><Logo /></Link>
          <nav className="hidden items-center gap-1 text-sm font-medium text-zinc-600 md:flex">
            <a href="#showcase" className="rounded-full px-3.5 py-2 transition hover:bg-zinc-950/5 hover:text-zinc-950">Showcase</a>
            <a href="#how" className="rounded-full px-3.5 py-2 transition hover:bg-zinc-950/5 hover:text-zinc-950">How it works</a>
            <a href={GITHUB_URL} target="_blank" rel="noreferrer" className="flex items-center gap-1.5 rounded-full px-3.5 py-2 transition hover:bg-zinc-950/5 hover:text-zinc-950">
              <Github size={15} /> GitHub
            </a>
          </nav>
          <div className="flex items-center gap-2">
            {loading ? null : user ? <UserMenu /> : (
              <>
                <button onClick={() => setAuth({ open: true })} className="hidden rounded-full px-4 py-2 text-sm font-medium text-zinc-700 transition hover:bg-zinc-950/5 min-[400px]:block">Log in</button>
                <button onClick={() => setAuth({ open: true })} className="rounded-full bg-zinc-950 px-4 py-2 text-sm font-medium text-white transition hover:bg-zinc-800">Get started</button>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative isolate flex min-h-[94dvh] flex-col items-center justify-center overflow-hidden px-4 pb-28 pt-24 sm:px-5 sm:pb-40 sm:pt-28">
        <WaveBackground />
        <a href={GITHUB_URL} target="_blank" rel="noreferrer" className="relative mb-6 flex items-center gap-2 rounded-full bg-white/70 py-1 pl-1 pr-3 text-[12px] sm:mb-7 sm:text-[13px] font-medium text-zinc-700 shadow-sm ring-1 ring-zinc-950/5 backdrop-blur transition hover:bg-white animate-[fade-up_600ms_ease_both]">
          <span className="rounded-full bg-zinc-950 px-2 py-0.5 text-[11px] font-semibold text-white">New</span>
          Open source · Compiles to Flutter
          <ArrowRight size={13} className="text-zinc-400" />
        </a>
        <h1 className="relative max-w-4xl text-center text-[40px] font-semibold leading-[1.04] tracking-[-0.045em] text-zinc-950 min-[400px]:text-[44px] sm:text-[68px] animate-[fade-up_700ms_80ms_ease_both]">
          Build <br className="sm:hidden" />
          <RotatingWord words={APP_KINDS} className="text-zinc-950" /> apps
          <br />
          <span className="text-shimmer">by chatting with AI</span>
        </h1>
        <p className="relative mt-5 max-w-xl text-center text-base leading-relaxed text-zinc-600 sm:text-lg animate-[fade-up_700ms_160ms_ease_both]">
          Describe your idea. Wolf designs every screen, lets you refine it like a design file, and turns it into a real Flutter app.
        </p>
        <div className="relative mt-8 w-full max-w-2xl sm:mt-9 animate-[fade-up_700ms_240ms_ease_both]">
          <PromptBox value={prompt} onChange={setPrompt} onSubmit={submit} busy={creating} ideas={PROMPT_IDEAS} />
          {(error || authError) && <p className="mt-3 text-center text-sm text-red-600">{error || authError}</p>}
        </div>
        <div className="relative -mx-4 mt-7 w-[calc(100%+2rem)] max-w-5xl sm:mx-0 sm:mt-8 sm:w-full animate-[fade-up_700ms_320ms_ease_both]">
          <PromptMarquee rows={MARQUEE_ROWS} onPick={setPrompt} />
        </div>
      </section>

      {/* Your apps (signed in) */}
      {user && projects && projects.length > 0 && (
        <section className="relative z-10 mx-auto -mt-16 max-w-7xl px-3 sm:-mt-24 sm:px-5">
          <div className="rounded-[28px] bg-white p-4 shadow-[0_-20px_60px_-30px_rgb(76_29_149/0.25)] ring-1 ring-zinc-950/5 sm:rounded-[32px] sm:p-8">
            <div className="mb-6 flex items-baseline justify-between">
              <h2 className="text-xl font-semibold tracking-tight">{user.name.split(' ')[0]}’s apps</h2>
              <span className="text-sm text-zinc-400">{projects.length} app{projects.length === 1 ? '' : 's'}</span>
            </div>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 sm:gap-4 lg:grid-cols-4 xl:grid-cols-5">
              {projects.map(p => <ProjectCard key={p.id} project={p} onDelete={() => removeProject(p.id)} />)}
            </div>
          </div>
        </section>
      )}

      {/* Watch it build */}
      <section className="relative mx-auto max-w-6xl px-4 pt-20 sm:px-5 sm:pt-28">
        <Reveal className="mx-auto mb-10 max-w-2xl text-center sm:mb-14">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-violet-600">Watch it build</p>
          <h2 className="mt-3 text-[32px] font-semibold leading-[1.1] tracking-[-0.035em] sm:text-5xl">From a sentence to screens in seconds</h2>
          <p className="mt-4 text-base text-zinc-600 sm:text-lg">Wolf plans the app, then builds it piece by piece while you watch. Every change is listed, and every one can be undone.</p>
        </Reveal>
        <Reveal>
          <BuildDemo examples={EXAMPLES} />
        </Reveal>
      </section>

      {/* Showcase */}
      <section id="showcase" className="mx-auto max-w-7xl px-5 py-20 sm:py-28">
        <Reveal className="mx-auto max-w-2xl text-center">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-violet-600">Showcase</p>
          <h2 className="mt-3 text-[32px] font-semibold leading-[1.1] tracking-[-0.035em] sm:text-5xl">One sentence in. A whole app out.</h2>
          <p className="mt-4 text-base text-zinc-600 sm:text-lg">Every screen below is a real Wolf app, rendered live from the same schema that compiles to Flutter.</p>
        </Reveal>
        {/* Desktop: a row of floating phones. Phones: a swipeable carousel. */}
        <Reveal className="mt-16 hidden flex-wrap items-end justify-center gap-10 sm:flex lg:gap-16" stagger={140}>
          {EXAMPLES.map((ex, i) => (
            <figure key={ex.name} className="group flex flex-col items-center" style={{ animation: `float 7s ease-in-out ${i * -2.3}s infinite` }}>
              <div className={`transition duration-500 group-hover:-translate-y-2 group-hover:rotate-0 ${i === 0 ? '-rotate-3' : i === 2 ? 'rotate-3' : 'lg:-translate-y-8'}`}>
                <PhoneThumbnail screen={ex.screen} theme={ex.theme} navigation={ex.navigation} width={270} />
              </div>
              <figcaption className="mt-7 max-w-[260px] text-center">
                <div className="text-[15px] font-semibold">{ex.name}</div>
                <div className="mt-1 text-sm text-zinc-500">“{ex.prompt}”</div>
              </figcaption>
            </figure>
          ))}
        </Reveal>
        <ShowcaseCarousel />
      </section>

      {/* How it works */}
      <section id="how" className="mx-auto max-w-7xl px-4 pb-20 sm:px-5 sm:pb-28">
        <Reveal className="grid gap-4 md:grid-cols-3" stagger={120}>
          {[
            { icon: MessageSquareText, title: 'Describe it', body: 'Tell Wolf what you want in plain words. It plans the screens, data and navigation, then builds them while you watch.' },
            { icon: MousePointerClick, title: 'Refine it', body: 'Click anything on a phone frame and tell Wolf what to change. Every change can be rolled back.' },
            { icon: Code2, title: 'Ship it', body: 'Wolf compiles your app to clean, idiomatic Flutter for iOS and Android. It’s your code: export it any time.' },
          ].map(({ icon: Icon, title, body }, i) => (
            <Spotlight key={title} className="group h-full overflow-hidden rounded-3xl bg-white p-7 ring-1 ring-zinc-950/5 transition duration-300 hover:-translate-y-1 hover:shadow-xl hover:shadow-violet-500/10">
              <div className="flex items-center justify-between">
                <span className="grid size-11 place-items-center rounded-2xl bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 text-white shadow-lg shadow-purple-500/25 transition duration-500 group-hover:rotate-[-8deg] group-hover:scale-110"><Icon size={20} /></span>
                <span className="text-5xl font-semibold tracking-tighter text-zinc-100 transition-colors duration-500 group-hover:text-violet-100">0{i + 1}</span>
              </div>
              <h3 className="mt-6 text-lg font-semibold tracking-tight">{title}</h3>
              <p className="mt-2 leading-relaxed text-zinc-600">{body}</p>
            </Spotlight>
          ))}
        </Reveal>

        <div className="relative mt-12 overflow-hidden rounded-[28px] bg-zinc-950 px-6 py-12 text-center text-white sm:mt-16 sm:rounded-[32px] sm:px-8 sm:py-14">
          <div aria-hidden className="hero-aurora absolute inset-0 opacity-70" style={{ background: 'radial-gradient(60% 120% at 20% 120%, #6366F1 0%, transparent 60%), radial-gradient(50% 120% at 80% 120%, #EC4899 0%, transparent 60%)' }} />
          <Smartphone className="relative mx-auto animate-[float_5s_ease-in-out_infinite] text-white/80" size={28} />
          <h2 className="relative mt-4 text-[26px] font-semibold leading-tight tracking-tight sm:text-4xl">Your next app is one prompt away</h2>
          <button onClick={() => { window.scrollTo({ top: 0, behavior: 'smooth' }); }} className="relative mt-7 inline-flex items-center gap-2 rounded-full bg-white px-5 py-2.5 text-sm font-semibold text-zinc-950 transition hover:bg-zinc-100">
            Start building <ArrowRight size={15} />
          </button>
        </div>
      </section>

      <footer className="border-t border-zinc-950/5">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 px-5 py-8 text-sm text-zinc-500 sm:flex-row">
          <Logo size={22} />
          <p>Open source under the MIT license.</p>
          <a href={GITHUB_URL} target="_blank" rel="noreferrer" className="flex items-center gap-1.5 hover:text-zinc-900"><Github size={15} /> Star on GitHub</a>
        </div>
      </footer>

      <AuthModal
        open={auth.open}
        reason={auth.reason}
        next="/"
        onBeforeRedirect={() => { if (sessionStorage.getItem(PENDING_KEY)) sessionStorage.setItem(RESUME_KEY, '1'); }}
        onClose={() => setAuth(a => ({ ...a, open: false }))}
      />
    </div>
  );
}

function ProjectCard({ project, onDelete }: { project: ProjectSummary; onDelete: () => void }) {
  const [menu, setMenu] = useState(false);
  const compactCards = useMediaQuery('(max-width: 639px)');
  const { screen, theme } = project.cover;
  return (
    <div className="group relative">
      <Link to={`/p/${project.id}`} className="block">
        <div className="relative h-44 overflow-hidden rounded-2xl sm:h-56 ring-1 ring-zinc-950/5 transition group-hover:ring-violet-300" style={{ background: `linear-gradient(160deg, ${theme?.primary ?? '#7C3AED'}22, ${theme?.primary ?? '#7C3AED'}08)` }}>
          {screen && theme ? (
            <div className="absolute left-1/2 top-4 -translate-x-1/2 transition duration-500 group-hover:-translate-y-1 sm:top-5">
              <PhoneThumbnail screen={screen} theme={theme} width={compactCards ? 120 : 150} />
            </div>
          ) : null}
        </div>
        <div className="mt-2.5 px-1">
          <div className="truncate text-[15px] font-medium">{project.name}</div>
          <div className="text-xs text-zinc-400">Edited {timeAgo(project.updated_at)}</div>
        </div>
      </Link>
      <button
        onClick={() => setMenu(!menu)}
        onBlur={() => setTimeout(() => setMenu(false), 150)}
        aria-label="App options"
        className="absolute right-2 top-2 grid size-8 place-items-center rounded-lg bg-white/90 text-zinc-600 shadow-sm ring-1 ring-zinc-950/5 transition focus:opacity-100 [@media(hover:hover)]:opacity-0 [@media(hover:hover)]:group-hover:opacity-100"
      >
        <MoreHorizontal size={16} />
      </button>
      {menu && (
        <div className="absolute right-2 top-11 z-20 w-40 rounded-xl bg-white p-1 shadow-xl ring-1 ring-zinc-950/5">
          <button onMouseDown={onDelete} className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-red-600 hover:bg-red-50">
            <Trash2 size={14} /> Delete
          </button>
        </div>
      )}
    </div>
  );
}

/** Phones only: the showcase as a swipeable, snapping carousel with dots. */
function ShowcaseCarousel() {
  const [active, setActive] = useState(0);
  const onScroll = (e: UIEvent<HTMLDivElement>) => {
    const el = e.currentTarget;
    const card = el.firstElementChild as HTMLElement | null;
    if (card) setActive(Math.round(el.scrollLeft / (card.offsetWidth + 16)));
  };
  return (
    <div className="mt-10 sm:hidden">
      <div onScroll={onScroll} className="-mx-5 flex snap-x snap-mandatory gap-4 overflow-x-auto px-[calc(50%-115px)] pb-6 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        {EXAMPLES.map((ex, i) => (
          <figure key={ex.name} className={`flex shrink-0 snap-center flex-col items-center transition duration-500 ${i === active ? 'scale-100 opacity-100' : 'scale-[0.92] opacity-60'}`}>
            <PhoneThumbnail screen={ex.screen} theme={ex.theme} navigation={ex.navigation} width={230} />
            <figcaption className="mt-5 w-[230px] text-center">
              <div className="text-[15px] font-semibold">{ex.name}</div>
              <div className="mt-1 text-sm text-zinc-500">“{ex.prompt}”</div>
            </figcaption>
          </figure>
        ))}
      </div>
      <div className="flex justify-center gap-1.5">
        {EXAMPLES.map((ex, i) => (
          <span key={ex.name} className={`h-1.5 rounded-full transition-all duration-300 ${i === active ? 'w-5 bg-zinc-900' : 'w-1.5 bg-zinc-300'}`} />
        ))}
      </div>
    </div>
  );
}
