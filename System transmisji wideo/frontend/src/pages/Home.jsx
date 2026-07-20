import { Link } from "react-router-dom"
import '../styles/home.css'

export const Home = () => {
    return (
        <main className="home-page">
            <section className="home-hero" aria-labelledby="home-title">
                <div className="home-hero__content">
                    <span className="eyebrow">System sterowania manipulatorem</span>
                    <h1 id="home-title">Steruj modelem za pomocą obrazu z kamery</h1>
                    <p className="home-hero__description">
                        Uruchom transmisję, aby przekazać obraz do systemu analizy
                        i sterować ramieniem robota w czasie rzeczywistym.
                    </p>
                    <Link className="button button--primary home-hero__action" to="/camera">
                        Przejdź do kamery
                        <span aria-hidden="true">→</span>
                    </Link>
                </div>

                <div className="home-visual" aria-hidden="true">
                    <div className="home-visual__grid" />
                    <div className="home-visual__orb home-visual__orb--large" />
                    <div className="home-visual__orb home-visual__orb--small" />
                    <div className="home-visual__panel">
                        <span className="home-visual__signal" />
                        <span>System gotowy</span>
                    </div>
                </div>
            </section>
        </main>
    )
}
