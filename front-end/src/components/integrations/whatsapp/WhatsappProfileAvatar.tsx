import { useEffect, useState } from "react";
import { resolveProfileAvatar } from "../../../features/integrations/format";

type Props = {
  src: string;
  alt: string;
  connected: boolean;
};

export default function WhatsappProfileAvatar({ src, alt, connected }: Props) {
  const [avatarSrc, setAvatarSrc] = useState(() => resolveProfileAvatar(src));

  useEffect(() => {
    setAvatarSrc(resolveProfileAvatar(src));
  }, [src]);

  function handleError() {
    setAvatarSrc(resolveProfileAvatar(""));
  }

  return (
    <div className="relative h-14 w-14 max-w-14 rounded-full">
      <img
        src={avatarSrc}
        alt={alt}
        className="h-14 w-14 rounded-full object-cover"
        onError={handleError}
        referrerPolicy="no-referrer"
      />
      <span
        className={`absolute bottom-0 right-0 h-3.5 w-3.5 rounded-full border-[1.5px] border-white dark:border-gray-900 ${
          connected ? "bg-success-500" : "bg-error-400"
        }`}
        aria-hidden
      />
    </div>
  );
}
