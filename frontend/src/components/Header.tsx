import { SidebarTrigger, useSidebar } from "@/components/ui/sidebar";

type HeaderProps = {
  title: string;
  dataset: string;
};

export default function Header({ title, dataset }: HeaderProps) {
  const { isMobile, openMobile } = useSidebar();
  const showBrand = isMobile && !openMobile;

  return (
    <header className="flex h-12 shrink-0 items-center gap-2 px-2">
      <SidebarTrigger />
      {showBrand ? <p className="shrink-0 text-sm font-medium">SQL Coach</p> : null}
      <p className="min-w-0 flex-1 truncate font-display">{title}</p>
      <p className="max-w-28 shrink-0 truncate text-muted-foreground sm:max-w-48">
        {dataset}
      </p>
    </header>
  );
}
