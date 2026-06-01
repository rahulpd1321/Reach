"use client";

import { VideoMetadata } from "@/lib/api";
import { Heart, MessageCircle, Eye, Clock, Hash, User } from "lucide-react";
import clsx from "clsx";

function formatNum(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

interface Props {
  video: VideoMetadata;
  label: string;
  accent: "violet" | "cyan";
}

export function VideoCard({ video, label, accent }: Props) {
  const isA = video.video_id === "A";
  const border =
    accent === "violet"
      ? "border-violet-500/40 shadow-violet-500/10"
      : "border-cyan-500/40 shadow-cyan-500/10";

  return (
    <article
      className={clsx(
        "glass rounded-2xl overflow-hidden shadow-xl flex flex-col",
        border,
        "border"
      )}
    >
      <div className="relative aspect-video bg-reach-card">
        {video.thumbnail_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={video.thumbnail_url}
            alt={video.title}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-reach-muted text-sm">
            No thumbnail
          </div>
        )}
        <span
          className={clsx(
            "absolute top-3 left-3 px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wide",
            isA ? "bg-violet-600/90" : "bg-cyan-600/90"
          )}
        >
          {label}
        </span>
        <span className="absolute top-3 right-3 px-2 py-1 rounded bg-black/60 text-xs capitalize">
          {video.platform}
        </span>
      </div>

      <div className="p-4 flex-1 flex flex-col gap-3">
        <h3 className="font-display font-semibold text-lg leading-snug line-clamp-2">
          {video.title}
        </h3>

        <div className="flex items-center gap-2 text-sm text-reach-muted">
          <User className="w-4 h-4 shrink-0" />
          <span className="truncate">{video.creator}</span>
          {video.follower_count != null && (
            <span className="text-xs bg-reach-border/50 px-2 py-0.5 rounded-full">
              {formatNum(video.follower_count)} followers
            </span>
          )}
        </div>

        <div className="grid grid-cols-3 gap-2 text-center">
          <Stat icon={Eye} value={formatNum(video.views)} label="Views" />
          <Stat icon={Heart} value={formatNum(video.likes)} label="Likes" />
          <Stat
            icon={MessageCircle}
            value={formatNum(video.comments)}
            label="Comments"
          />
        </div>

        <div
          className={clsx(
            "rounded-xl p-3 text-center",
            isA ? "bg-violet-500/15" : "bg-cyan-500/15"
          )}
        >
          <p className="text-xs text-reach-muted uppercase tracking-wider">
            Engagement Rate
          </p>
          <p className="text-2xl font-display font-bold gradient-text">
            {video.engagement_rate.toFixed(2)}%
          </p>
          <p className="text-[10px] text-reach-muted mt-1">
            (likes + comments) / views × 100
          </p>
        </div>

        <div className="flex flex-wrap gap-1.5 text-xs">
          {video.upload_date && (
            <span className="flex items-center gap-1 text-reach-muted">
              <Clock className="w-3 h-3" />
              {video.upload_date}
            </span>
          )}
          {video.duration_seconds != null && (
            <span className="text-reach-muted">
              · {Math.floor(video.duration_seconds / 60)}:
              {String(video.duration_seconds % 60).padStart(2, "0")}
            </span>
          )}
        </div>

        {video.hashtags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            <Hash className="w-3 h-3 text-reach-muted mt-0.5 shrink-0" />
            {video.hashtags.slice(0, 6).map((tag) => (
              <span
                key={tag}
                className="text-xs text-cyan-400/90 bg-cyan-500/10 px-1.5 py-0.5 rounded"
              >
                #{tag}
              </span>
            ))}
          </div>
        )}

        <p className="text-xs text-reach-muted line-clamp-3 border-t border-reach-border pt-2 mt-auto">
          {video.transcript_preview}
        </p>
      </div>
    </article>
  );
}

function Stat({
  icon: Icon,
  value,
  label,
}: {
  icon: React.ComponentType<{ className?: string }>;
  value: string;
  label: string;
}) {
  return (
    <div className="bg-reach-bg/50 rounded-lg py-2">
      <Icon className="w-4 h-4 mx-auto text-reach-muted mb-1" />
      <p className="font-semibold text-sm">{value}</p>
      <p className="text-[10px] text-reach-muted">{label}</p>
    </div>
  );
}
