import { useState, useMemo, useCallback } from 'react';
import { DrivingPlan, DayPlan, Party, Member } from '@/types/carpool';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Pencil, Users, FileText } from 'lucide-react';
import { cn } from '@/lib/utils';
import { DayPlanEditDialog } from './DayPlanEditDialog';

interface PlanViewerProps {
  plan: DrivingPlan;
  onPlanChange: (plan: DrivingPlan) => void;
  members: Member[];
}

const DAY_NAMES: Record<string, string> = {
  MONDAY: 'Monday',
  TUESDAY: 'Tuesday',
  WEDNESDAY: 'Wednesday',
  THURSDAY: 'Thursday',
  FRIDAY: 'Friday',
};

const formatTime = (time: number): string => {
  const hours = Math.floor(time / 100);
  const minutes = time % 100;
  return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
};

interface Transfer {
  id: string;
  passenger: string;
  fromParty: Party;
  toParty: Party;
  hasTimeWarning: boolean;
}

export function PlanViewer({ plan, onPlanChange, members }: PlanViewerProps) {
  const [weekFilter, setWeekFilter] = useState<'summary' | 'all' | 'A' | 'B'>('summary');
  const [personFilter, setPersonFilter] = useState('');
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editingDayPlan, setEditingDayPlan] = useState<DayPlan | null>(null);

  // Create lookup map: initials -> Member
  const membersByInitials = useMemo(() => {
    const map = new Map<string, Member>();
    members.forEach(m => map.set(m.initials.toLowerCase(), m));
    return map;
  }, [members]);

  // Format initials as "FirstName (Initials)" with non-breaking space
  const formatPerson = useCallback((initials: string) => {
    const member = membersByInitials.get(initials.toLowerCase());
    if (member) {
      return `${member.firstName}\u00A0(${member.initials})`;
    }
    return initials;
  }, [membersByInitials]);

  const filteredDayPlans = useMemo(() => {
    return Object.entries(plan.dayPlans)
      .filter(([_, dayPlan]) => {
        if (weekFilter === 'A' && !dayPlan.dayOfWeekABCombo.isWeekA) return false;
        if (weekFilter === 'B' && dayPlan.dayOfWeekABCombo.isWeekA) return false;
        
        if (personFilter.trim()) {
          const query = personFilter.trim().toLowerCase();
          const hasPersonInParties = dayPlan.parties.some(party => {
            // Check driver by initials or name
            const driverMember = membersByInitials.get(party.driver.toLowerCase());
            const driverMatches = party.driver.toLowerCase().includes(query) ||
              (driverMember && (
                driverMember.firstName.toLowerCase().includes(query) ||
                driverMember.lastName.toLowerCase().includes(query)
              ));
            
            // Check passengers by initials or name
            const passengerMatches = party.passengers.some(p => {
              const passengerMember = membersByInitials.get(p.toLowerCase());
              return p.toLowerCase().includes(query) ||
                (passengerMember && (
                  passengerMember.firstName.toLowerCase().includes(query) ||
                  passengerMember.lastName.toLowerCase().includes(query)
                ));
            });
            
            return driverMatches || passengerMatches;
          });
          if (!hasPersonInParties) return false;
        }
        
        return true;
      })
      .sort(([a], [b]) => parseInt(a) - parseInt(b));
  }, [plan, weekFilter, personFilter, membersByInitials]);

  const handleEditDay = (dayPlan: DayPlan) => {
    setEditingDayPlan(dayPlan);
    setEditDialogOpen(true);
  };

  const handleApplyTransfers = (dayPlan: DayPlan, transfers: Transfer[]) => {
    const dayKey = Object.entries(plan.dayPlans).find(
      ([_, dp]) => dp.dayOfWeekABCombo.uniqueNumber === dayPlan.dayOfWeekABCombo.uniqueNumber
    )?.[0];

    if (!dayKey) return;

    const updatedParties = [...dayPlan.parties].map(party => ({
      ...party,
      passengers: [...party.passengers],
    }));

    transfers.forEach(transfer => {
      // Find source party and remove passenger
      const sourceParty = updatedParties.find(
        p => p.driver === transfer.fromParty.driver && p.time === transfer.fromParty.time
      );
      if (sourceParty) {
        sourceParty.passengers = sourceParty.passengers.filter(p => p !== transfer.passenger);
      }

      // Find target party and add passenger
      const targetParty = updatedParties.find(
        p => p.driver === transfer.toParty.driver && p.time === transfer.toParty.time
      );
      if (targetParty) {
        targetParty.passengers.push(transfer.passenger);
      }
    });

    const updatedPlan: DrivingPlan = {
      ...plan,
      dayPlans: {
        ...plan.dayPlans,
        [dayKey]: {
          ...dayPlan,
          parties: updatedParties,
        },
      },
    };

    onPlanChange(updatedPlan);
  };

  const renderPartyLine = (party: Party, filterQuery: string, isLast: boolean) => {
    const query = filterQuery.trim().toLowerCase();
    const driverMember = membersByInitials.get(party.driver.toLowerCase());
    const isDriverHighlighted = query && (
      party.driver.toLowerCase().includes(query) ||
      (driverMember && (
        driverMember.firstName.toLowerCase().includes(query) ||
        driverMember.lastName.toLowerCase().includes(query)
      ))
    );
    const driverPrefix = isDriverHighlighted ? '*' : '';
    
    const passengersFormatted = party.passengers.map(p => {
      const member = membersByInitials.get(p.toLowerCase());
      if (member) {
        return `${member.firstName}\u00A0(${member.initials})`;
      }
      return p;
    });
    
    const passengersText = passengersFormatted.length > 0 
      ? ' · ' + passengersFormatted.join(' · ')
      : '';

    return (
      <div key={`${party.driver}-${party.time}`} className={cn(
        "text-sm leading-tight py-0.5",
        !isLast && "border-b border-border/30"
      )}>
        <span className="text-muted-foreground font-mono">[{formatTime(party.time)}]</span>
        {' '}
        <span className={cn("font-semibold", isDriverHighlighted && "text-primary")}>
          {driverPrefix}{formatPerson(party.driver)}
        </span>
        {passengersText && (
          <span className="text-muted-foreground">{passengersText}</span>
        )}
      </div>
    );
  };

  const renderDayRow = ([dayKey, dayPlan]: [string, DayPlan]) => {
    const { dayOfWeekABCombo, parties } = dayPlan;
    const schoolboundParties = parties
      .filter(p => p.schoolbound === true)
      .sort((a, b) => a.time - b.time);
    const homeboundParties = parties
      .filter(p => p.schoolbound === false)
      .sort((a, b) => a.time - b.time);
    
    return (
      <tr key={dayKey} className="border-b border-border/50 hover:bg-muted/30 transition-colors">
        <td className="py-1.5 px-4 align-top whitespace-nowrap font-medium">
          <div>
            {DAY_NAMES[dayOfWeekABCombo.dayOfWeek]}
          </div>
          <div className="text-xs text-muted-foreground">
            ({dayOfWeekABCombo.isWeekA ? 'A' : 'B'})
          </div>
        </td>
        <td className="py-1.5 px-4 align-top">
          {schoolboundParties.length > 0 ? (
            <div>
              {schoolboundParties.map((party, idx) => renderPartyLine(party, personFilter, idx === schoolboundParties.length - 1))}
            </div>
          ) : (
            <span className="text-muted-foreground text-sm">—</span>
          )}
        </td>
        <td className="py-1.5 px-4 align-top">
          {homeboundParties.length > 0 ? (
            <div>
              {homeboundParties.map((party, idx) => renderPartyLine(party, personFilter, idx === homeboundParties.length - 1))}
            </div>
          ) : (
            <span className="text-muted-foreground text-sm">—</span>
          )}
        </td>
        <td className="py-1.5 px-2 align-top">
          <button 
            onClick={() => handleEditDay(dayPlan)}
            className="p-1.5 rounded hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
            title="Edit day plan"
          >
            <Pencil className="h-4 w-4" />
          </button>
        </td>
      </tr>
    );
  };

  return (
    <div className="space-y-4 animate-fade-in">
      <Tabs value={weekFilter} onValueChange={(v) => setWeekFilter(v as typeof weekFilter)}>
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <TabsList className="h-9">
            <TabsTrigger value="summary" className="text-sm px-4 gap-2">
              <FileText className="h-4 w-4" />
              Summary
            </TabsTrigger>
            <TabsTrigger value="A" className="text-sm px-4">Week A</TabsTrigger>
            <TabsTrigger value="B" className="text-sm px-4">Week B</TabsTrigger>
            <TabsTrigger value="all" className="text-sm px-4">Complete Plan</TabsTrigger>
          </TabsList>

          {weekFilter !== 'summary' && (
            <div className="relative w-full sm:w-56">
              <Input
                placeholder="filter by name or initials"
                value={personFilter}
                onChange={(e) => setPersonFilter(e.target.value)}
                className="h-9 text-sm pl-3 pr-3"
              />
            </div>
          )}
        </div>

        <TabsContent value="summary" className="mt-4">
          <div className="p-4 rounded-lg bg-muted/50 border border-border/50">
            <p className="text-sm text-foreground whitespace-pre-wrap">{plan.summary}</p>
          </div>
        </TabsContent>

        {['A', 'B', 'all'].map((tabValue) => (
          <TabsContent key={tabValue} value={tabValue} className="mt-4 space-y-4">
            {/* Table */}
            <div className="rounded-lg border border-border overflow-hidden">
              <table className="w-full">
                <thead>
                  <tr className="bg-muted/50 border-b border-border">
                    <th className="py-2 px-4 text-left text-sm font-semibold text-foreground w-28">Day</th>
                    <th className="py-2 px-4 text-left text-sm font-semibold text-foreground">Schoolbound</th>
                    <th className="py-2 px-4 text-left text-sm font-semibold text-foreground">Homebound</th>
                    <th className="py-2 px-2 w-12"></th>
                  </tr>
                </thead>
                <tbody>
                  {filteredDayPlans.map(renderDayRow)}
                </tbody>
              </table>
            </div>

            {filteredDayPlans.length === 0 && (
              <div className="text-center py-12 border border-border rounded-lg">
                <Users className="h-10 w-10 text-muted-foreground mx-auto mb-3" />
                <p className="text-muted-foreground text-sm">No day plans match your filters</p>
              </div>
            )}
          </TabsContent>
        ))}
      </Tabs>

      <DayPlanEditDialog
        open={editDialogOpen}
        onOpenChange={setEditDialogOpen}
        dayPlan={editingDayPlan}
        onApplyTransfers={handleApplyTransfers}
        members={members}
      />
    </div>
  );
}
