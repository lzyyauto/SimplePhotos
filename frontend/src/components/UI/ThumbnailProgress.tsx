import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef } from 'react';
import { api } from '@/services/api';

const formatCount = (count: number) => count.toLocaleString('zh-CN');

export const ThumbnailProgress = () => {
  const queryClient = useQueryClient();
  const previousReady = useRef<number | null>(null);
  const { data, isPending, isError, refetch } = useQuery({
    queryKey: ['thumbnail-progress'],
    queryFn: api.getThumbnailProgress,
    refetchInterval: 30_000,
    refetchOnWindowFocus: true,
  });

  useEffect(() => {
    if (!data) return;
    if (previousReady.current !== null && previousReady.current !== data.ready) {
      void queryClient.invalidateQueries({ queryKey: ['folders'] });
    }
    previousReady.current = data.ready;
  }, [data, queryClient]);

  if (isError && !data) {
    return (
      <div className="mx-auto max-w-7xl px-4 pt-4 md:px-6 lg:px-8">
        <div className="flex items-center justify-between gap-3 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200">
          <span>暂时无法读取缩略图进度</span>
          <button type="button" onClick={() => void refetch()} className="min-h-11 shrink-0 rounded-lg px-3 font-medium underline underline-offset-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-600">
            重试
          </button>
        </div>
      </div>
    );
  }

  const total = data?.total ?? 0;
  const ready = data?.ready ?? 0;
  const remaining = data?.remaining ?? 0;
  const roundedPercent = total > 0 ? Math.round((ready / total) * 1_000) / 10 : 0;
  const percent = ready < total ? Math.min(roundedPercent, 99.9) : roundedPercent;

  return (
    <section aria-label="缩略图生成进度" className="mx-auto max-w-7xl px-4 pt-4 md:px-6 lg:px-8">
      <div className="rounded-2xl border border-gray-200 bg-white/90 px-4 py-3 shadow-sm dark:border-white/10 dark:bg-gray-900/90 sm:px-5">
        <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-1">
          <div>
            <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100">缩略图生成进度</h2>
            <p className="mt-0.5 text-sm text-gray-600 dark:text-gray-300">
              {isPending ? '正在读取统计…' : total === 0 ? '当前没有已索引的媒体' : `已生成 ${formatCount(ready)} / 当前已索引 ${formatCount(total)}，还差 ${formatCount(remaining)}（含失败）`}
            </p>
          </div>
          <span className="text-lg font-semibold tabular-nums text-gray-900 dark:text-gray-100" aria-hidden="true">
            {isPending ? '—' : `${percent.toFixed(1)}%`}
          </span>
        </div>

        <div
          role="progressbar"
          aria-label="已生成缩略图比例"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={percent}
          aria-valuetext={`${formatCount(ready)} / ${formatCount(total)}，失败 ${formatCount(data?.failed ?? 0)}`}
          className="mt-3 h-2 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700"
        >
          <div className="h-full rounded-full bg-emerald-600 transition-[width] duration-300 motion-reduce:transition-none dark:bg-emerald-400" style={{ width: `${percent}%` }} />
        </div>

        <dl className="mt-3 grid grid-cols-3 gap-2 text-xs sm:gap-4 sm:text-sm">
          <div><dt className="text-gray-600 dark:text-gray-300">待处理</dt><dd className="font-semibold tabular-nums text-gray-900 dark:text-gray-100">{isPending ? '—' : formatCount(data?.pending ?? 0)}</dd></div>
          <div><dt className="text-gray-600 dark:text-gray-300">处理中</dt><dd className="font-semibold tabular-nums text-gray-900 dark:text-gray-100">{isPending ? '—' : formatCount(data?.processing ?? 0)}</dd></div>
          <div><dt className="text-gray-600 dark:text-gray-300">失败</dt><dd className="font-semibold tabular-nums text-rose-700 dark:text-rose-300">{isPending ? '—' : formatCount(data?.failed ?? 0)}</dd></div>
        </dl>
        <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">按当前已索引且仍存在的媒体统计；失败需单独处理。</p>
      </div>
    </section>
  );
};
