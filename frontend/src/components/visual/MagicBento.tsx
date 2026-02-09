import { useRef, useEffect, useState, useCallback } from 'react'

export interface MagicBentoProps {
  textAutoHide?: boolean
  enableStars?: boolean
  enableSpotlight?: boolean
  enableBorderGlow?: boolean
  enableTilt?: boolean
  enableMagnetism?: boolean
  clickEffect?: boolean
  spotlightRadius?: number
  particleCount?: number
  glowColor?: string
  disableAnimations?: boolean
}

export interface BentoItem {
  id: string
  label: string
  title: string
  subtitle: string
  span: string
  isLarge?: boolean
}

const BENTO_ITEMS: BentoItem[] = [
  { id: '1', label: 'Insights', title: 'Analytics', subtitle: 'Track user behavior', span: 'col-span-1 md:col-span-3 row-span-1', isLarge: false },
  { id: '2', label: 'Overview', title: 'Dashboard', subtitle: 'Centralized data view', span: 'col-span-1 md:col-span-3 row-span-1', isLarge: false },
  { id: '3', label: 'Teamwork', title: 'Collaboration', subtitle: 'Work together seamlessly', span: 'col-span-1 md:col-span-6 md:row-span-2 row-span-1', isLarge: true },
  { id: '4', label: 'Efficiency', title: 'Automation', subtitle: 'Streamline workflows', span: 'col-span-1 md:col-span-6 md:row-span-2 row-span-1', isLarge: true },
  { id: '5', label: 'Connectivity', title: 'Integration', subtitle: 'Connect favorite tools', span: 'col-span-1 md:col-span-3 row-span-1', isLarge: false },
  { id: '6', label: 'Protection', title: 'Security', subtitle: 'Enterprise-grade protection', span: 'col-span-1 md:col-span-3 row-span-1', isLarge: false },
]

export default function MagicBento({
  textAutoHide = true,
  enableStars = true,
  enableSpotlight = true,
  enableBorderGlow = true,
  enableTilt = false,
  enableMagnetism = false,
  clickEffect = true,
  spotlightRadius = 400,
  particleCount = 12,
  glowColor = '132, 0, 255',
  disableAnimations = false,
}: MagicBentoProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [clickRipple, setClickRipple] = useState<{ id: string; x: number; y: number } | null>(null)

  const handleCardClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>, id: string) => {
      if (!clickEffect || disableAnimations) return
      const rect = e.currentTarget.getBoundingClientRect()
      setClickRipple({ id, x: e.clientX - rect.left, y: e.clientY - rect.top })
      setTimeout(() => setClickRipple(null), 600)
    },
    [clickEffect, disableAnimations]
  )

  return (
    <div
      ref={containerRef}
      className="relative w-full min-h-[480px] overflow-hidden rounded-3xl border border-white/10 bg-white/5 p-6 backdrop-blur-md"
      style={{
        boxShadow: '0 0 0 1px rgba(255,255,255,0.05), 0 20px 80px rgba(132,0,255,0.12)',
      }}
    >
      {enableStars && !disableAnimations && (
        <StarsLayer particleCount={particleCount} />
      )}

      <div className="relative z-10 grid grid-cols-1 md:grid-cols-12 gap-6 auto-rows-auto min-h-[400px]">
        {BENTO_ITEMS.map((item) => (
          <BentoCard
            key={item.id}
            item={item}
            enableSpotlight={enableSpotlight}
            enableBorderGlow={enableBorderGlow}
            enableTilt={enableTilt}
            enableMagnetism={enableMagnetism}
            textAutoHide={textAutoHide}
            clickEffect={clickEffect}
            disableAnimations={disableAnimations}
            spotlightRadius={spotlightRadius}
            glowColor={glowColor}
            onClick={handleCardClick}
            ripple={clickRipple?.id === item.id ? clickRipple : null}
          />
        ))}
      </div>
    </div>
  )
}

function StarsLayer({ particleCount }: { particleCount: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const resize = () => {
      const parent = canvas.parentElement
      if (!parent) return
      const rect = parent.getBoundingClientRect()
      canvas.width = rect.width
      canvas.height = rect.height
    }
    resize()
    window.addEventListener('resize', resize)

    const particles = Array.from({ length: particleCount }, () => ({
      x: Math.random(),
      y: Math.random(),
      size: 1.5 + Math.random() * 1.5,
      speed: 0.15 + Math.random() * 0.2,
      opacity: 0.2 + Math.random() * 0.25,
    }))

    let raf = 0
    const animate = () => {
      raf = requestAnimationFrame(animate)
      const w = canvas.width
      const h = canvas.height
      if (w === 0 || h === 0) return
      ctx.clearRect(0, 0, w, h)
      const t = performance.now() * 0.001
      particles.forEach((p) => {
        const x = (p.x * w + Math.sin(t + p.y * 10) * 15) % (w + 30)
        const y = (p.y * h + Math.cos(t * 0.7 + p.x * 10) * 10) % (h + 30)
        ctx.beginPath()
        ctx.arc(x, y, p.size, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(255,255,255,${p.opacity * (0.4 + 0.4 * Math.sin(t * 2 + p.x))})`
        ctx.fill()
      })
    }
    animate()
    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener('resize', resize)
    }
  }, [particleCount])

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 w-full h-full pointer-events-none rounded-3xl"
      aria-hidden
    />
  )
}

interface BentoCardProps {
  item: BentoItem
  enableSpotlight: boolean
  enableBorderGlow: boolean
  enableTilt: boolean
  enableMagnetism: boolean
  textAutoHide: boolean
  clickEffect: boolean
  disableAnimations: boolean
  spotlightRadius: number
  glowColor: string
  onClick: (e: React.MouseEvent<HTMLDivElement>, id: string) => void
  ripple: { x: number; y: number } | null
}

function BentoCard({
  item,
  enableSpotlight,
  enableBorderGlow,
  enableTilt,
  enableMagnetism,
  textAutoHide,
  disableAnimations,
  spotlightRadius,
  glowColor,
  onClick,
  ripple,
}: BentoCardProps) {
  const cardRef = useRef<HTMLDivElement>(null)
  const [mouse, setMouse] = useState({ x: 50, y: 50 })
  const [tilt, setTilt] = useState({ x: 0, y: 0 })
  const [magnet, setMagnet] = useState({ x: 0, y: 0 })

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      const el = e.currentTarget
      const rect = el.getBoundingClientRect()
      const x = ((e.clientX - rect.left) / rect.width) * 100
      const y = ((e.clientY - rect.top) / rect.height) * 100
      setMouse({ x, y })
      if (enableTilt && !disableAnimations) {
        const cx = rect.left + rect.width / 2
        const cy = rect.top + rect.height / 2
        setTilt({
          x: (e.clientY - cy) / (rect.height / 2),
          y: (e.clientX - cx) / (rect.width / 2),
        })
      }
      if (enableMagnetism && !disableAnimations) {
        const cx = 50
        const cy = 50
        setMagnet({
          x: (x - cx) * 0.15,
          y: (y - cy) * 0.15,
        })
      }
    },
    [enableTilt, enableMagnetism, disableAnimations]
  )

  const handleMouseLeave = useCallback(() => {
    setMouse({ x: 50, y: 50 })
    setTilt({ x: 0, y: 0 })
    setMagnet({ x: 0, y: 0 })
  }, [])

  const transform =
    enableTilt && !disableAnimations
      ? `perspective(800px) rotateX(${tilt.x * -4}deg) rotateY(${tilt.y * 4}deg) translate(${magnet.x}px, ${magnet.y}px)`
      : enableMagnetism && !disableAnimations
        ? `translate(${magnet.x}px, ${magnet.y}px)`
        : undefined

  const baseShadow = `0 0 0 1px rgba(255,255,255,0.05), 0 20px 80px rgba(${glowColor}, 0.12)`
  const hoverShadow = enableBorderGlow && !disableAnimations
    ? `0 0 0 1px rgba(255,255,255,0.08), 0 0 40px rgba(${glowColor}, 0.2), 0 20px 80px rgba(${glowColor}, 0.15)`
    : baseShadow

  return (
    <div
      ref={cardRef}
      className={`group relative overflow-hidden rounded-3xl border border-white/10 bg-white/5 backdrop-blur transition-all duration-300 ${item.span} ${item.isLarge ? 'p-8' : 'p-7'}`}
      style={{
        transform,
        transition: disableAnimations ? 'none' : 'transform 0.2s ease-out, box-shadow 0.3s ease',
        ['--mx' as string]: `${mouse.x}%`,
        ['--my' as string]: `${mouse.y}%`,
        ['--spotlight-radius' as string]: `${spotlightRadius}px`,
        boxShadow: baseShadow,
      }}
      onMouseMove={handleMouseMove}
      onClick={(e) => onClick(e, item.id)}
      onMouseEnter={() => {
        if (cardRef.current && enableBorderGlow && !disableAnimations) {
          cardRef.current.style.boxShadow = hoverShadow
        }
      }}
      onMouseLeave={() => {
        if (cardRef.current) {
          cardRef.current.style.boxShadow = baseShadow
        }
        handleMouseLeave()
      }}
    >
      {enableSpotlight && (
        <div
          className="pointer-events-none absolute inset-0 rounded-3xl opacity-50"
          style={{
            background: `radial-gradient(circle at var(--mx) var(--my), rgba(255,255,255,0.08) 0%, transparent var(--spotlight-radius))`,
          }}
        />
      )}

      {ripple && (
        <span
          className="absolute pointer-events-none rounded-full bg-white/30 animate-ping"
          style={{
            left: ripple.x,
            top: ripple.y,
            width: 24,
            height: 24,
            marginLeft: -12,
            marginTop: -12,
            animationDuration: '0.6s',
          }}
        />
      )}

      <div className="relative z-10 flex h-full flex-col">
        <p className="text-sm text-white/70">{item.label}</p>
        <h3 className="mt-2 text-2xl font-semibold text-white md:text-3xl">
          {item.title}
        </h3>
        <p
          className={`mt-2 text-sm leading-relaxed text-white/60 transition-opacity duration-200 ${
            textAutoHide ? 'opacity-0 group-hover:opacity-100' : ''
          }`}
        >
          {item.subtitle}
        </p>
      </div>
    </div>
  )
}
