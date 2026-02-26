import Link from "next/link";

type Props = {
  id: number;
  title: string;
  category: string;
  keyIngredients: string[];
  timeMin: number | null;
  servings: number | null;
  viewCount: number;
};

export function RecipeCard({ id, title, category, keyIngredients, timeMin, servings, viewCount }: Props) {
  return (
    <Link href={`/recipes/${id}`} className="block group">
      <div className="border rounded-xl p-4 h-full hover:shadow-md hover:border-primary/30 transition-all bg-card">
        {/* 카테고리 뱃지 */}
        <span className="inline-block text-xs font-medium px-2 py-0.5 rounded-full bg-primary/10 text-primary mb-2">
          {category}
        </span>
        {/* 제목 */}
        <h3 className="font-semibold text-sm sm:text-base line-clamp-2 group-hover:text-primary transition-colors mb-2">
          {title}
        </h3>
        {/* 재료 태그 */}
        <div className="flex flex-wrap gap-1 mb-3">
          {keyIngredients.slice(0, 4).map((ing) => (
            <span key={ing} className="text-xs px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
              {ing}
            </span>
          ))}
          {keyIngredients.length > 4 && (
            <span className="text-xs text-muted-foreground">+{keyIngredients.length - 4}</span>
          )}
        </div>
        {/* 메타 정보 */}
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          {timeMin && <span>{timeMin}분</span>}
          {servings && <span>{servings}인분</span>}
          {viewCount > 0 && <span>조회 {viewCount.toLocaleString()}</span>}
        </div>
      </div>
    </Link>
  );
}
