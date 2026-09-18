import { useEffect, useRef } from 'react'

/**
 * Hero 背景：Canvas 2D 流场（无第三方依赖）。
 * 逻辑：等距格点上按噪声角度画短线段，逐帧平移相位形成缓慢流动；页面不可见或
 * 用户偏好减少动效时停止绘制。-- 设计依据见 docs/03-decisions/r001-adr-0008。
 */
interface Particle {
  x: number
  y: number
  vx: number
  vy: number
}

const COUNT = 90
const SPEED = 0.32

export default function FlowField({ className }: { className?: string }) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const context = canvas.getContext('2d')
    if (!context) return

    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (reduced) return

    let width = 0
    let height = 0
    let raf = 0
    let running = true
    const particles: Particle[] = []

    const resize = () => {
      const ratio = Math.min(window.devicePixelRatio || 1, 2)
      const rect = canvas.getBoundingClientRect()
      width = rect.width
      height = rect.height
      canvas.width = Math.floor(width * ratio)
      canvas.height = Math.floor(height * ratio)
      context.setTransform(ratio, 0, 0, ratio, 0, 0)
    }

    const seed = () => {
      particles.length = 0
      for (let index = 0; index < COUNT; index += 1) {
        particles.push({
          x: Math.random() * width,
          y: Math.random() * height,
          vx: Math.cos(index) * SPEED,
          vy: Math.sin(index * 1.7) * SPEED,
        })
      }
    }

    // 角度场：用两点正弦叠加构造平滑流场，成本低且无需噪声库
    const angleAt = (x: number, y: number, t: number) =>
      Math.sin(x * 0.0035 + t * 0.00022) * 1.6 + Math.cos(y * 0.0042 - t * 0.00018) * 1.4

    const draw = (time: number) => {
      if (!running) return
      context.clearRect(0, 0, width, height)
      context.lineWidth = 1

      for (const particle of particles) {
        const angle = angleAt(particle.x, particle.y, time)
        particle.vx = Math.cos(angle) * SPEED
        particle.vy = Math.sin(angle) * SPEED
        particle.x += particle.vx
        particle.y += particle.vy

        if (particle.x < -20) particle.x = width + 20
        if (particle.x > width + 20) particle.x = -20
        if (particle.y < -20) particle.y = height + 20
        if (particle.y > height + 20) particle.y = -20

        context.strokeStyle = 'rgba(124, 240, 196, 0.16)'
        context.beginPath()
        context.moveTo(particle.x, particle.y)
        context.lineTo(particle.x - particle.vx * 12, particle.y - particle.vy * 12)
        context.stroke()
      }
      raf = window.requestAnimationFrame(draw)
    }

    const onVisibility = () => {
      running = document.visibilityState === 'visible'
      if (running) raf = window.requestAnimationFrame(draw)
      else window.cancelAnimationFrame(raf)
    }

    resize()
    seed()
    raf = window.requestAnimationFrame(draw)
    window.addEventListener('resize', resize)
    document.addEventListener('visibilitychange', onVisibility)

    return () => {
      running = false
      window.cancelAnimationFrame(raf)
      window.removeEventListener('resize', resize)
      document.removeEventListener('visibilitychange', onVisibility)
    }
  }, [])

  return <canvas ref={canvasRef} className={className} aria-hidden />
}
