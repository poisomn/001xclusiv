document.addEventListener("DOMContentLoaded", () => {
    if (typeof gsap === "undefined" || typeof ScrollTrigger === "undefined") {
        return;
    }

    gsap.registerPlugin(ScrollTrigger);

    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const progressBar = document.querySelector(".home-scroll-progress__bar");
    const updateScrollProgress = () => {
        if (!progressBar) {
            return;
        }

        const scrollableHeight = document.documentElement.scrollHeight - window.innerHeight;
        const progress = scrollableHeight > 0 ? window.scrollY / scrollableHeight : 0;
        progressBar.style.transform = `scaleY(${Math.min(Math.max(progress, 0), 1)})`;
    };

    updateScrollProgress();
    window.addEventListener("scroll", updateScrollProgress, { passive: true });

    const ambientSections = document.querySelectorAll("[data-ambient]");
    ambientSections.forEach((section) => {
        const resetAmbient = () => {
            section.style.setProperty("--ambient-x", "50%");
            section.style.setProperty("--ambient-y", "50%");
        };

        resetAmbient();

        section.addEventListener("pointermove", (event) => {
            const rect = section.getBoundingClientRect();
            const x = ((event.clientX - rect.left) / rect.width) * 100;
            const y = ((event.clientY - rect.top) / rect.height) * 100;
            section.style.setProperty("--ambient-x", `${x.toFixed(2)}%`);
            section.style.setProperty("--ambient-y", `${y.toFixed(2)}%`);
        });

        section.addEventListener("pointerleave", resetAmbient);
    });

    // --- HERO ANIMATION ---
    const svg = document.querySelector(".hero-gsap svg");
    if (svg && !prefersReducedMotion) {
        const elements = svg.querySelectorAll("*");

        gsap.set(elements, {
            x: () => gsap.utils.random(-500, 500),
            y: () => gsap.utils.random(-500, 500),
            rotation: () => gsap.utils.random(-720, 720),
            scale: 0,
            opacity: 0,
        });

        const tl = gsap.timeline({
            repeat: -1,
            repeatDelay: 0.65,
            yoyo: true,
        });

        tl.to(elements, {
            x: 0,
            y: 0,
            scale: 1,
            opacity: 1,
            rotation: 0,
            ease: "power4.inOut",
            stagger: 0.0125,
            duration: 0.75,
        });

        svg.addEventListener("mouseenter", () => tl.timeScale(0.15));
        svg.addEventListener("mouseleave", () => tl.timeScale(1));
    }

    if (prefersReducedMotion) {
        return;
    }

    const heroIntroElements = [
        ".section-kicker",
        ".home-legacy-copy__title",
        ".scroll-hero__payoff",
        ".home-legacy-copy__text",
        ".home-hero__actions a, .home-hero__actions button, .home-hero__stats .hero-stat",
        ".hero-spotlight__card--static",
    ];

    heroIntroElements.forEach((selector, index) => {
        const elements = document.querySelectorAll(selector);
        if (!elements.length) {
            return;
        }

        gsap.fromTo(
            elements,
            { autoAlpha: 0, y: 32 },
            {
                autoAlpha: 1,
                y: 0,
                duration: 0.75,
                delay: 0.08 * index,
                stagger: 0.08,
                ease: "power3.out",
            }
        );
    });

    const revealSelectors = [
        ".trust-pill",
        ".home-immersive-band__copy",
        ".immersive-metric-card",
        ".editorial-manifesto",
        ".editorial-visual-card",
        ".category-showcase__card",
        ".home-product-card",
        ".home-lookbook-card",
        ".arrival-card",
        ".home-journey__step",
        ".promise-card",
        ".testimonial-card",
        ".home-cinematic-cta",
        ".newsletter-cta",
    ];

    gsap.utils.toArray(revealSelectors.join(",")).forEach((element) => {
        gsap.fromTo(
            element,
            { autoAlpha: 0, y: 48, scale: 0.98 },
            {
                autoAlpha: 1,
                y: 0,
                scale: 1,
                duration: 0.9,
                ease: "power3.out",
                scrollTrigger: {
                    trigger: element,
                    start: "top 86%",
                    once: true,
                },
            }
        );
    });

    gsap.utils.toArray(".parallax-image").forEach((image) => {
        const triggerElement = image.closest(
            ".category-showcase__card, .editorial-visual-card, .home-lookbook-card, .arrival-card, .home-cinematic-cta"
        );
        if (!triggerElement) {
            return;
        }

        gsap.set(image, {
            scale: 1.14,
            yPercent: -10,
            force3D: true,
        });

        gsap.to(image, {
            yPercent: 10,
            ease: "none",
            scrollTrigger: {
                trigger: triggerElement,
                start: "top 92%",
                end: "bottom 8%",
                scrub: 1.1,
            },
        });
    });

    gsap.utils.toArray(".home-immersive-band, .home-brand-promise, .home-cinematic-cta").forEach((section) => {
        gsap.fromTo(
            section,
            { backgroundPosition: "50% 0%" },
            {
                backgroundPosition: "50% 100%",
                ease: "none",
                scrollTrigger: {
                    trigger: section,
                    start: "top bottom",
                    end: "bottom top",
                    scrub: true,
                },
            }
        );
    });

    // --- SCROLL ANIMATIONS ---

    // Cards Animation
    const cards = document.querySelectorAll(".scroll-container .card");
    if (cards.length > 0) {
        cards.forEach((card, index) => {
            gsap.fromTo(card,
                { y: "80%", rotate: -45 + (90 / (cards.length + 1)) * index },
                {
                    y: "20%",
                    rotate: 45, // Adjust rotation logic if needed to match CSS exactly
                    scrollTrigger: {
                        trigger: card,
                        start: "top bottom",
                        end: "bottom top",
                        scrub: true,
                    }
                }
            );
        });
    }

    // Cover Image Clip Path
    const coverImage = document.querySelector(".scroll-container .cover-image");
    if (coverImage) {
        gsap.fromTo(coverImage,
            { clipPath: "polygon(100% 0%, 100% 0%, 100% 100%, 100% 100%)" }, // Approximate start
            {
                clipPath: "polygon(100% 0%, 0% 0%, 0% 100%, 100% 100%)", // Approximate end
                scrollTrigger: {
                    trigger: coverImage,
                    start: "top 60%",
                    end: "bottom 35%",
                    scrub: true,
                }
            }
        );
    }

    // Reviews
    const reviews = document.querySelectorAll(".scroll-container .review");
    reviews.forEach((review) => {
        gsap.fromTo(review,
            { y: "40%", opacity: 0 },
            {
                y: "0%",
                opacity: 1,
                scrollTrigger: {
                    trigger: review,
                    start: "top bottom",
                    end: "center center",
                    scrub: 1,
                }
            }
        );
    });

    // Spinner
    const spinner = document.querySelector(".scroll-container .spinner");
    if (spinner) {
        gsap.to(spinner, {
            "--radial-progress": 1,
            scrollTrigger: {
                trigger: spinner,
                start: "top bottom",
                end: "bottom top",
                scrub: true,
            }
        });
    }
});
