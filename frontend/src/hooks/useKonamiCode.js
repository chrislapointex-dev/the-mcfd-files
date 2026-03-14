import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'

const SEQUENCE = [
  'ArrowUp', 'ArrowUp', 'ArrowDown', 'ArrowDown',
  'ArrowLeft', 'ArrowRight', 'ArrowLeft', 'ArrowRight',
  'b', 'a',
]

export default function useKonamiCode() {
  const navigate = useNavigate()
  const indexRef = useRef(0)

  useEffect(() => {
    const handler = (e) => {
      if (e.key === SEQUENCE[indexRef.current]) {
        indexRef.current++
        if (indexRef.current === SEQUENCE.length) {
          indexRef.current = 0
          document.body.style.outline = '3px solid #10b981'
          setTimeout(() => {
            document.body.style.outline = ''
            navigate('/r2d2')
          }, 400)
        }
      } else {
        indexRef.current = 0
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [navigate])
}
