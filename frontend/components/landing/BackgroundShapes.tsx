export default function BackgroundShapes() {
  return (
    <div aria-hidden className="pointer-events-none">
      <svg className="absolute left-0 top-8 w-72 opacity-30" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
        <rect x="0" y="0" width="200" height="200" fill="#ffdede" />
      </svg>

      <svg className="absolute right-0 top-40 w-96 opacity-20" viewBox="0 0 300 200" xmlns="http://www.w3.org/2000/svg">
        <circle cx="50" cy="50" r="60" fill="#e6f7ff" />
      </svg>

      <svg className="absolute left-1/2 -translate-x-1/2 bottom-20 w-80 opacity-25" viewBox="0 0 200 80" xmlns="http://www.w3.org/2000/svg">
        <rect x="0" y="0" width="200" height="80" fill="#fff8e6" />
      </svg>
    </div>
  )
}
