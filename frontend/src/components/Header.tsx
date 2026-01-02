import { Car, Users, CalendarDays } from 'lucide-react';
import { ViewMode } from '@/types/carpool';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface HeaderProps {
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
  hasPlan: boolean;
}

export function Header({ viewMode, onViewModeChange, hasPlan }: HeaderProps) {
  return (
    <header className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-50">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-primary/10">
              <Car className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h1 className="text-xl font-semibold text-foreground">Carpool Planner</h1>
              <p className="text-sm text-muted-foreground">For Teachers</p>
            </div>
          </div>
          
          <nav className="flex items-center gap-1 bg-muted/50 p-1 rounded-xl">
            <Button
              variant={viewMode === 'members' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => onViewModeChange('members')}
              className={cn(
                "gap-2 transition-all",
                viewMode === 'members' && "shadow-sm"
              )}
            >
              <Users className="h-4 w-4" />
              Members
            </Button>
            <Button
              variant={viewMode === 'plan' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => onViewModeChange('plan')}
              className={cn(
                "gap-2 transition-all",
                viewMode === 'plan' && "shadow-sm"
              )}
              disabled={!hasPlan}
            >
              <CalendarDays className="h-4 w-4" />
              Driving Plan
            </Button>
          </nav>
        </div>
      </div>
    </header>
  );
}
