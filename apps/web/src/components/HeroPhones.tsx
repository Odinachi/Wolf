import type { Example } from '../examples';
import { usePointerParallax } from '../lib/motion';
import { PhoneThumbnail } from '../renderer/PhoneFrame';

/** Phones floating at the edges of the hero, drifting with the cursor. Wide screens only. */
export function HeroPhones({ left, right }: { left: Example; right: Example }) {
  const p = usePointerParallax();
  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 hidden xl:block">
      <div className="absolute left-[3%] top-[24%]" style={{ transform: `translate(${p.x * -18}px, ${p.y * -12}px) rotate(${-12 + p.x * 2}deg)` }}>
        <div className="animate-[float_8s_ease-in-out_infinite] opacity-90">
          <PhoneThumbnail screen={left.screen} theme={left.theme} navigation={left.navigation} width={210} />
        </div>
      </div>
      <div className="absolute right-[3%] top-[30%]" style={{ transform: `translate(${p.x * -26}px, ${p.y * -16}px) rotate(${11 + p.x * 2}deg)` }}>
        <div className="animate-[float_9s_ease-in-out_-3s_infinite] opacity-90">
          <PhoneThumbnail screen={right.screen} theme={right.theme} navigation={right.navigation} width={200} />
        </div>
      </div>
    </div>
  );
}
