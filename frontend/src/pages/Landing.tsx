import { Link } from 'react-router-dom'
import Threads from '../components/visual/Threads'

export default function Landing() {
  return (
    <main className="relative min-h-screen w-screen overflow-hidden bg-[#060714] bg-gradient-to-b from-[#060714] via-[#08051a] to-[#05030f] left-0 right-0">
      {/* Threads full-viewport background — full bleed */}
      <Threads
        className="absolute inset-0 left-0 right-0 z-0"
        amplitude={1}
        distance={0}
        enableMouseInteraction
      />

      {/* Vignette / radial overlays for contrast */}
      <div
        className="pointer-events-none absolute inset-0 left-0 right-0 z-[1] bg-[radial-gradient(ellipse_at_center,rgba(132,0,255,0.12),transparent_55%)]"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute inset-0 left-0 right-0 z-[1] [background:radial-gradient(1200px_600px_at_50%_40%,rgba(255,255,255,0.06),transparent_60%)]"
        aria-hidden
      />
      {/* Gradient overlay so text stays readable over Threads */}
      <div
        className="pointer-events-none absolute inset-0 left-0 right-0 z-[2] bg-gradient-to-b from-black/40 via-transparent to-black/50"
        aria-hidden
      />

      {/* Floating pill navbar */}
      <header className="absolute top-6 left-1/2 z-20 w-[min(900px,calc(100%-2rem))] -translate-x-1/2">
        <div className="flex items-center justify-between rounded-full border border-white/10 bg-white/5 px-6 py-3 backdrop-blur-md">
          <div className="flex items-center gap-3 text-white/90">
            <span className="h-8 w-8 rounded-full bg-white/10" />
            <span className="font-semibold">TariffShock</span>
          </div>
          <nav className="flex items-center gap-6 text-sm text-white/70">
            <a className="hover:text-white transition-colors" href="/">
              Home
            </a>
            <a className="hover:text-white transition-colors" href="/docs">
              Docs
            </a>
          </nav>
        </div>
      </header>

      {/* Center hero content — badge, headline, 2 CTAs */}
      <section className="relative z-10 flex min-h-screen flex-col items-center justify-center px-6 text-center pointer-events-none">
        <div className="pointer-events-auto flex flex-col items-center pt-16">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-xs text-white/70 backdrop-blur">
            <span className="h-2 w-2 rounded-full bg-[#8400ff]" />
            Explainable Risk Modeling
          </div>
          <h1 className="max-w-4xl text-balance text-4xl font-semibold tracking-tight text-white sm:text-6xl">
            Understand global tariffs. Before they hurt.
            <br />

          </h1>
          <p className="mt-6 max-w-xl text-lg text-white/60">
            Simulate tariff shocks and see which Canadian sectors are most exposed. And why.
          </p>
          <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
            <Link
              to="/dashboard"
              className="inline-flex items-center justify-center rounded-full border border-white/20 bg-white px-6 py-3 text-sm font-medium text-[#060714] hover:bg-white/90 transition-colors"
            >
              Open Dashboard
            </Link>
            <a
              href="/docs"
              className="inline-flex items-center justify-center rounded-full border border-white/10 bg-white/5 px-6 py-3 text-sm font-medium text-white/90 backdrop-blur hover:bg-white/10 hover:border-white/20 transition-colors"
            >
              Learn More
            </a>
          </div>
          <p className="mt-8 text-xs text-white/40 font-medium">Built for policymakers, analysts, and researchers</p>
        </div>
      </section>
    </main>
  )
}
