import { Link } from 'react-router-dom'
import '../styles/Placeholder.css'

export default function PlaceholderPage({ title }: { title: string }) {
  return (
    <div className="placeholder-page">
      <h1 className="placeholder-page-title">{title}</h1>
      <p className="placeholder-page-note">Static placeholder — wire up routing and data when the backend is ready.</p>
      <Link to="/mainpage" className="placeholder-page-back">
        ← Back to home
      </Link>
    </div>
  )
}
