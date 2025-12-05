document.addEventListener("DOMContentLoaded", () => {
    gsap.registerPlugin(ScrollTrigger);

    // --- HERO ANIMATION ---
    const svg = document.querySelector(".hero-gsap svg");
    if (svg) {
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
