import { useEffect, useRef } from "react";
import lottie, { type AnimationItem } from "lottie-web";

// Renders a Lottie animation (the preview returned by /render/preview).
export function LottiePlayer({
  data,
  className = "",
  loop = true,
  autoplay = true,
}: {
  data: Record<string, unknown> | null;
  className?: string;
  loop?: boolean;
  autoplay?: boolean;
}) {
  const container = useRef<HTMLDivElement>(null);
  const anim = useRef<AnimationItem | null>(null);

  useEffect(() => {
    if (!container.current || !data) return;
    anim.current?.destroy();
    anim.current = lottie.loadAnimation({
      container: container.current,
      renderer: "svg",
      loop,
      autoplay,
      animationData: JSON.parse(JSON.stringify(data)),
    });
    return () => {
      anim.current?.destroy();
      anim.current = null;
    };
  }, [data, loop, autoplay]);

  return <div ref={container} className={className} />;
}
