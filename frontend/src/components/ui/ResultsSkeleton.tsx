import { motion } from 'framer-motion'

function SkeletonCard({ delay = 0 }: { delay?: number }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay }}
      className="card p-5"
    >
      {/* Top row */}
      <div className="flex items-start gap-3">
        <div className="skeleton w-7 h-7 rounded-lg flex-shrink-0" />
        <div className="flex-1 space-y-2">
          <div className="skeleton h-4 w-48 rounded" />
          <div className="skeleton h-3 w-24 rounded" />
        </div>
      </div>

      {/* Summary lines */}
      <div className="mt-4 pl-10 space-y-2">
        <div className="skeleton h-3 w-full rounded" />
        <div className="skeleton h-3 w-5/6 rounded" />
        <div className="skeleton h-3 w-4/6 rounded" />
      </div>

      {/* Action buttons */}
      <div className="mt-4 pl-10 flex gap-2">
        <div className="skeleton h-7 w-28 rounded-xl" />
        <div className="skeleton h-7 w-24 rounded-xl" />
      </div>
    </motion.div>
  )
}

export default function ResultsSkeleton() {
  return (
    <div className="mt-8 flex flex-col gap-4">
      <div className="skeleton h-3 w-40 rounded mb-1" />
      {[0, 1, 2, 3, 4].map(i => (
        <SkeletonCard key={i} delay={i * 0.06} />
      ))}
    </div>
  )
}
