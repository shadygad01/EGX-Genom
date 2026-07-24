import type { ReactNode } from "react";
import { EmptyState } from "./States";
import styles from "./DataTable.module.css";

export interface DataTableColumn<T> {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
  align?: "left" | "right" | "center";
  width?: string;
}

export interface DataTableProps<T> {
  columns: DataTableColumn<T>[];
  rows: T[];
  getRowKey: (row: T, index: number) => string;
  onRowClick?: (row: T) => void;
  emptyTitle?: string;
  emptyDetail?: string;
}

const alignClass: Record<string, string> = {
  right: styles.alignRight,
  center: styles.alignCenter,
};

/** The one tabular-data renderer for the app -- every ranked list, holdings
 * table, or history log goes through this rather than a bespoke <table>. */
export function DataTable<T>({
  columns,
  rows,
  getRowKey,
  onRowClick,
  emptyTitle = "No data",
  emptyDetail,
}: DataTableProps<T>) {
  if (rows.length === 0) {
    return <EmptyState title={emptyTitle} detail={emptyDetail} />;
  }

  return (
    <div className={styles.wrap}>
      <table className={styles.table}>
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col.key} style={{ width: col.width }} className={alignClass[col.align ?? "left"] ?? ""}>
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr
              key={getRowKey(row, index)}
              className={onRowClick ? styles.clickableRow : ""}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              tabIndex={onRowClick ? 0 : undefined}
              onKeyDown={
                onRowClick
                  ? (e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        onRowClick(row);
                      }
                    }
                  : undefined
              }
            >
              {columns.map((col) => (
                <td key={col.key} className={alignClass[col.align ?? "left"] ?? ""}>
                  {col.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
