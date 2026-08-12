import { EmptyState } from "./states";
import { PageHeading } from "./page-heading";

export function PlaceholderPage({ description, title }: { description: string; title: string }) {
  return <><PageHeading description={description} title={title} /><EmptyState description={`${title} tools will be connected in the next dedicated frontend phase.`} title={`${title} is ready for its data`} /></>;
}
