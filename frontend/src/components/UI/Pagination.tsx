import { Button } from './Button';

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

export const Pagination = ({ 
  currentPage, 
  totalPages, 
  onPageChange 
}: PaginationProps) => {
  return (
    <div className="flex items-center justify-center gap-2 mt-4">
      <Button
        variant="secondary"
        onClick={() => onPageChange(currentPage - 1)}
        disabled={currentPage <= 1}
      >
        上一页
      </Button>
      <span className="px-4 py-2">
        {currentPage} / {totalPages}
      </span>
      <Button
        variant="secondary"
        onClick={() => onPageChange(currentPage + 1)}
        disabled={currentPage >= totalPages}
      >
        下一页
      </Button>
    </div>
  );
}; 