import { useState } from 'react';
import { Member, DrivingPlan, ViewMode } from '@/types/carpool';
import { useLocalStorage } from '@/hooks/useLocalStorage';
import { Header } from '@/components/Header';
import { MembersPanel } from '@/components/MembersPanel';
import { PlanControls } from '@/components/PlanControls';
import { PlanViewer } from '@/components/PlanViewer';
import { Toaster } from '@/components/ui/toaster';

const Index = () => {
  const [members, setMembers] = useLocalStorage<Member[]>('carpool-members', []);
  const [plan, setPlan] = useLocalStorage<DrivingPlan | null>('carpool-plan', null);
  const [viewMode, setViewMode] = useState<ViewMode>('members');

  const handleViewPlan = () => {
    setViewMode('plan');
  };

  return (
    <div className="min-h-screen bg-background">
      <Header 
        viewMode={viewMode} 
        onViewModeChange={setViewMode}
        hasPlan={!!plan}
      />
      
      <main className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Sidebar / Controls */}
          <aside className="lg:col-span-4 xl:col-span-3 order-2 lg:order-1">
            <div className="lg:sticky lg:top-24">
              <PlanControls
                members={members}
                plan={plan}
                onPlanChange={setPlan}
                onViewPlan={handleViewPlan}
              />
            </div>
          </aside>
          
          {/* Main Content */}
          <section className="lg:col-span-8 xl:col-span-9 order-1 lg:order-2">
            {viewMode === 'members' ? (
              <MembersPanel
                members={members}
                onMembersChange={setMembers}
              />
            ) : plan ? (
              <PlanViewer
                plan={plan}
                onPlanChange={setPlan}
                members={members}
              />
            ) : (
              <div className="text-center py-16">
                <p className="text-muted-foreground">
                  No plan loaded. Generate a new plan or import from JSON.
                </p>
              </div>
            )}
          </section>
        </div>
      </main>
    </div>
  );
};

export default Index;
