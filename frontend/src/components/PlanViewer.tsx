import { useState, useMemo, useCallback } from 'react';
import { format } from 'date-fns';
import { DrivingPlan, DayPlan, Party, Member } from '@/types/carpool';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Pencil, Users, FileText, Download, Trash2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { DayPlanEditDialog } from './DayPlanEditDialog';
import { useToast } from '@/hooks/use-toast';

interface PlanViewerProps {
  plan: DrivingPlan;
  onPlanChange: (plan: DrivingPlan) => void;
  members: Member[];
  referenceDate?: Date;
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

interface SelectedMemberInfo {
  initials: string;
  dayPlan: DayPlan;
  party: Party;
}

export function PlanViewer({ plan, onPlanChange, members, referenceDate }: PlanViewerProps) {
  const [weekFilter, setWeekFilter] = useState<'summary' | 'all' | 'A' | 'B'>('summary');
  const [personFilter, setPersonFilter] = useState('');
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editingDayPlan, setEditingDayPlan] = useState<DayPlan | null>(null);
  const [selectedMember, setSelectedMember] = useState<SelectedMemberInfo | null>(null);
  const { toast } = useToast();

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

  // Helper function to generate schedule link
  const getScheduleUrl = (initials: string): string | null => {
    if (!plan.memberIdMap || !plan.scheduleUrlTemplate) {
      return null;
    }
    const memberId = plan.memberIdMap[initials];
    if (!memberId) {
      return null;
    }
    // Format reference date as YYYY-MM-DD, fallback to today if not available
    const dateToUse = referenceDate || new Date();
    const dateStr = format(dateToUse, 'yyyy-MM-dd');
    // Replace DATE and TEACHER_ID placeholders
    return plan.scheduleUrlTemplate
      .replace('DATE', dateStr)
      .replace('TEACHER_ID', memberId);
  };

  const renderMemberInfoPane = () => {
    if (!selectedMember) return null;

    const member = membersByInitials.get(selectedMember.initials.toLowerCase());
    if (!member) return null;

    const dayCombo = selectedMember.dayPlan.dayOfWeekABCombo;
    const dayLabel = `${DAY_NAMES[dayCombo.dayOfWeek]}, Week ${dayCombo.isWeekA ? 'A' : 'B'}`;
    
    const timeInfo = selectedMember.party.schoolbound
      ? selectedMember.dayPlan.schoolboundTimeInfoByInitials?.[selectedMember.initials]
      : selectedMember.dayPlan.homeboundTimeInfoByInitials?.[selectedMember.initials];

    const scheduleUrl = getScheduleUrl(selectedMember.initials);

    // Build party display text
    const partyMembers = [selectedMember.party.driver, ...selectedMember.party.passengers];
    const partyDisplay = partyMembers
      .map(initials => formatPerson(initials))
      .join(' · ');

    return (
      <div className="rounded-lg border border-primary/30 bg-primary/5 p-4 space-y-3">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-xs text-muted-foreground uppercase tracking-wide font-medium">Member Details</p>
            <p className="text-lg font-semibold">
              {member.firstName} {member.lastName}
              <span className="text-muted-foreground ml-2">({member.initials})</span>
            </p>
          </div>
          <button
            onClick={() => setSelectedMember(null)}
            className="text-muted-foreground hover:text-foreground transition-colors"
            title="Close"
          >
            ✕
          </button>
        </div>

        <div className="space-y-2 text-sm">
          <p className="text-muted-foreground">
            <span className="font-medium">Day:</span> {dayLabel}
          </p>

          <div className="space-y-1">
            <p className="font-medium">Time Source Information</p>
            <div className="pl-3 space-y-1 text-sm">
              {timeInfo?.timetableTime !== null && (
                <p className="text-muted-foreground">
                  <span className="font-medium">Timetable:</span>{' '}
                  {formatTime(timeInfo?.timetableTime || 0)}
                  {scheduleUrl && (
                    <>
                      {' '}
                      <a
                        href={scheduleUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary hover:underline"
                        title="View schedule in WebUntis"
                      >
                        (View schedule)
                      </a>
                    </>
                  )}
                </p>
              )}
              {timeInfo?.customPrefTime !== null && (
                <p className={cn(
                  "font-medium",
                  timeInfo?.customPrefTime === timeInfo?.effectiveTime
                    ? "text-amber-600 dark:text-amber-400"
                    : "text-muted-foreground"
                )}>
                  Custom Preference: {formatTime(timeInfo?.customPrefTime || 0)}
                  {timeInfo?.customPrefTime === timeInfo?.effectiveTime && (
                    <span className="ml-2 text-xs">(Used - overrides timetable)</span>
                  )}
                </p>
              )}
              <p className="font-medium">
                Effective Time: {formatTime(timeInfo?.effectiveTime || 0)}
              </p>
            </div>
          </div>

          <div className="space-y-1 pt-2">
            <p className="font-medium">Party</p>
            <p className="text-muted-foreground pl-3">
              [{formatTime(selectedMember.party.time)}] {partyDisplay}
            </p>
          </div>

          {selectedMember.party.poolName && (
            <div className="space-y-1 pt-2">
              <p className="font-medium">Pool</p>
              <p className="text-muted-foreground pl-3 font-mono text-xs bg-muted/50 p-2 rounded">
                {selectedMember.party.poolName}
              </p>
            </div>
          )}
        </div>
      </div>
    );
  };

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

  const handleExportPlan = () => {
    const data = JSON.stringify(plan, null, 2);
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const dateStr = referenceDate ? format(referenceDate, 'yyyy-MM-dd') : '';
    a.download = dateStr ? `driving-plan-${dateStr}.json` : 'driving-plan.json';
    a.click();
    URL.revokeObjectURL(url);
    toast({ title: 'Exported', description: 'Driving plan exported to JSON.' });
  };

  const handleDiscardPlan = () => {
    onPlanChange(null);
    toast({ title: 'Plan discarded', description: 'You can now generate a new plan.' });
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

  const renderPartyLine = (party: Party, dayPlan: DayPlan, filterQuery: string, isLast: boolean) => {
    const query = filterQuery.trim().toLowerCase();
    const driverMember = membersByInitials.get(party.driver.toLowerCase());
    const isDriverHighlighted = query && (
      party.driver.toLowerCase().includes(query) ||
      (driverMember && (
        driverMember.firstName.toLowerCase().includes(query) ||
        driverMember.lastName.toLowerCase().includes(query)
      ))
    );
    const driverPrefix = party.isDesignatedDriver ? '*' : '';
    const isDriverSelected = selectedMember?.initials === party.driver && selectedMember?.party === party;
    
    const passengersFormatted = party.passengers.map(p => {
      const member = membersByInitials.get(p.toLowerCase());
      const isPassengerHighlighted = query && (
        p.toLowerCase().includes(query) ||
        (member && (
          member.firstName.toLowerCase().includes(query) ||
          member.lastName.toLowerCase().includes(query)
        ))
      );
      const displayText = member ? `${member.firstName}\u00A0(${member.initials})` : p;
      const isPassengerSelected = selectedMember?.initials === p && selectedMember?.party === party;
      
      return {
        text: displayText,
        initials: p,
        highlighted: isPassengerHighlighted,
        selected: isPassengerSelected
      };
    });

    return (
      <div key={`${party.driver}-${party.time}`} className={cn(
        "text-sm leading-tight py-0.5 pl-[7ch]",
        !isLast && "border-b border-border/30"
      )} style={{ textIndent: '-7ch' }}>
        <span className="text-muted-foreground font-mono">[{formatTime(party.time)}]</span>
        {' '}
        <button
          onClick={() => setSelectedMember({ initials: party.driver, dayPlan, party })}
          className={cn(
            "font-semibold cursor-pointer transition-all",
            isDriverHighlighted && "text-primary",
            isDriverSelected && "text-primary font-bold underline",
            "hover:text-primary hover:font-bold"
          )}
        >
          {driverPrefix}{formatPerson(party.driver)}
        </button>
        {passengersFormatted.length > 0 && (
          <span className="text-muted-foreground">
            {' · '}
            {passengersFormatted.map((p, idx) => (
              <span key={idx}>
                {idx > 0 && ' · '}
                <button
                  onClick={() => setSelectedMember({ initials: p.initials, dayPlan, party })}
                  className={cn(
                    "cursor-pointer transition-all",
                    p.highlighted && "text-primary font-semibold",
                    p.selected && "text-primary font-bold underline",
                    "hover:text-primary hover:font-bold"
                  )}
                >
                  {p.text}
                </button>
              </span>
            ))}
          </span>
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
    
    // Check if selected member belongs to this day
    const isSelectedDayPlan = selectedMember?.dayPlan.dayOfWeekABCombo.uniqueNumber === dayPlan.dayOfWeekABCombo.uniqueNumber;
    
    return (
      <>
        <tr key={dayKey} className="group border-b border-border/50 hover:bg-muted/30 transition-colors">
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
              {schoolboundParties.map((party, idx) => renderPartyLine(party, dayPlan, personFilter, idx === schoolboundParties.length - 1))}
            </div>
          ) : (
            <span className="text-muted-foreground text-sm">—</span>
          )}
        </td>
        <td className="py-1.5 px-4 align-top">
          {homeboundParties.length > 0 ? (
            <div>
              {homeboundParties.map((party, idx) => renderPartyLine(party, dayPlan, personFilter, idx === homeboundParties.length - 1))}
            </div>
          ) : (
            <span className="text-muted-foreground text-sm">—</span>
          )}
        </td>
        <td className="py-1.5 px-2 align-top">
          <button 
            onClick={() => handleEditDay(dayPlan)}
            className="p-1.5 rounded hover:bg-muted transition-all text-muted-foreground hover:text-foreground opacity-0 group-hover:opacity-100"
            title="Edit day plan"
          >
            <Pencil className="h-4 w-4" />
          </button>
        </td>
      </tr>
      {isSelectedDayPlan && selectedMember && (
        <tr key={`info-${dayKey}`}>
          <td colSpan={4} className="bg-primary/5 border-b border-border/50 p-4">
            {renderMemberInfoPane()}
          </td>
        </tr>
      )}
      </>
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

          <div className="flex items-center gap-2">
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
            <Button variant="outline" size="sm" onClick={handleExportPlan} className="h-9" title="Export JSON">
              <Download className="h-4 w-4" />
            </Button>
            <Button variant="outline" size="sm" onClick={handleDiscardPlan} className="h-9" title="Discard Plan">
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>

        <TabsContent value="summary" className="mt-4">
          {(() => {
            // Parse summary text: "- Name (Initials): Count"
            const lines = plan.summary.split('\n').filter(line => line.trim());
            const driveCounts = new Map<number, Array<{ name: string; initials: string }>>();
            
            lines.forEach(line => {
              const match = line.match(/^-\s*(.+?)\s*\(([^)]+)\):\s*(\d+)$/);
              if (match) {
                const [, name, initials, countStr] = match;
                const count = parseInt(countStr, 10);
                if (!driveCounts.has(count)) {
                  driveCounts.set(count, []);
                }
                driveCounts.get(count)!.push({ name: name.trim(), initials: initials.trim() });
              }
            });

            // Sort by count descending, and alphabetically by name within each count
            const sortedCounts = Array.from(driveCounts.entries())
              .sort((a, b) => b[0] - a[0])
              .map(([count, people]) => [
                count,
                people.sort((a, b) => a.name.localeCompare(b.name))
              ] as [number, Array<{ name: string; initials: string }>]);

            // Helper function to generate schedule link
            const getScheduleUrl = (initials: string): string | null => {
              if (!plan.memberIdMap || !plan.scheduleUrlTemplate) {
                return null;
              }
              const memberId = plan.memberIdMap[initials];
              if (!memberId) {
                return null;
              }
              // Format reference date as YYYY-MM-DD, fallback to today if not available
              const dateToUse = referenceDate || new Date();
              const dateStr = format(dateToUse, 'yyyy-MM-dd');
              // Replace DATE and TEACHER_ID placeholders
              return plan.scheduleUrlTemplate
                .replace('DATE', dateStr)
                .replace('TEACHER_ID', memberId);
            };

            return (
              <div className="rounded-lg border border-border overflow-hidden">
                {sortedCounts.map(([count, people], idx) => (
                  <div 
                    key={count} 
                    className={cn(
                      "bg-card",
                      idx !== sortedCounts.length - 1 && "border-b border-border"
                    )}
                  >
                    <div className="bg-muted/50 px-4 py-2 border-b border-border/50">
                      <h3 className="text-sm font-semibold text-foreground">
                        Driving {count} {count === 1 ? 'time' : 'times'}
                      </h3>
                    </div>
                    <div className="px-4 py-3">
                      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2">
                        {people.map((person) => {
                          const scheduleUrl = getScheduleUrl(person.initials);
                          const content = (
                            <>
                              {person.name}
                              <span className="ml-1">({person.initials})</span>
                            </>
                          );
                          
                          if (scheduleUrl) {
                            return (
                              <a
                                key={person.initials}
                                href={scheduleUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-sm text-muted-foreground hover:font-bold cursor-pointer transition-all"
                                title="View schedule in WebUntis"
                              >
                                {content}
                              </a>
                            );
                          }
                          
                          return (
                            <div 
                              key={person.initials}
                              className="text-sm text-foreground"
                            >
                              {content}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            );
          })()}
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
                  {filteredDayPlans.map(([dayKey, dayPlan], idx) => {
                    const needsSeparator = tabValue === 'all' &&
                      dayPlan.dayOfWeekABCombo.dayOfWeek === 'MONDAY';

                    return (
                      <>
                        {needsSeparator && (
                          <tr key={`separator-${dayKey}`}>
                            <td colSpan={4} className="py-0">
                              <div className="relative">
                                <div className="absolute inset-0 flex items-center px-4">
                                  <div className="w-full border-t-2 border-primary/20" />
                                </div>
                                <div className="relative flex justify-center">
                                  <span className="bg-background px-3 py-2 text-xs font-medium text-muted-foreground uppercase tracking-wide">
                                    {dayPlan.dayOfWeekABCombo.isWeekA ? 'Week A' : 'Week B'}
                                  </span>
                                </div>
                              </div>
                            </td>
                          </tr>
                        )}
                        {renderDayRow([dayKey, dayPlan])}
                      </>
                    );
                  })}
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
