"use client";

import { Menu } from "lucide-react";
import { useState } from "react";

import { AppSidebar } from "@/components/layout/app-sidebar";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetDescription, SheetTitle, SheetTrigger } from "@/components/ui/sheet";

export function MobileNav() {
  const [open, setOpen] = useState(false);

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button variant="secondary" size="icon" aria-label="Open navigation">
          <Menu className="size-4" />
        </Button>
      </SheetTrigger>
      <SheetContent side="left" className="w-[88vw] max-w-[340px] p-0" aria-describedby="mobile-navigation-description">
        <SheetTitle className="sr-only">Navigation</SheetTitle>
        <SheetDescription id="mobile-navigation-description" className="sr-only">Primary application navigation. Demo and pending-backend routes are labelled.</SheetDescription>
        <AppSidebar className="border-r-0" onNavigate={() => setOpen(false)} />
      </SheetContent>
    </Sheet>
  );
}
