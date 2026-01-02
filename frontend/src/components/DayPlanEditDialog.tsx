import { useState, useMemo, useCallback } from 'react';
import { DayPlan, Party, Member } from '@/types/carpool';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { AlertTriangle, ArrowRight, Search, Trash2, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { ScrollArea } from '@/components/ui/scroll-area';

interface Transfer {
  id: string;
  passenger: string;
  fromParty: Party;
  toParty: Party;
  hasTimeWarning: boolean;
}

interface DayPlanEditDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  dayPlan: DayPlan | null;
  onApplyTransfers: (dayPlan: DayPlan, transfers: Transfer[]) => void;
  members: Member[];
}

const DAY_NAMES: Record<string, string> = {
  MONDAY: 'Monday',
  TUESDAY: 'Tuesday',
  WEDNESDAY: 'Wednesday',
  THURSDAY: 'Thursday',
  FRIDAY: 'Friday',
};


type Step = 'select-passenger' | 'select-target';

export function DayPlanEditDialog({
  open,
  onOpenChange,
  dayPlan,
  onApplyTransfers,
  members,
}: DayPlanEditDialogProps) {
  const [step, setStep] = useState<Step>('select-passenger');
  const [passengerSearch, setPassengerSearch] = useState('');
  const [targetSearch, setTargetSearch] = useState('');
  const [selectedPassenger, setSelectedPassenger] = useState<{ passenger: string; party: Party } | null>(null);
  const [transfers, setTransfers] = useState<Transfer[]>([]);

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

  const formatTime = (time: number): string => {
    const hours = Math.floor(time / 100);
    const minutes = time % 100;
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
  };

  // Check if a query matches an initials string (by initials or name)
  // Returns: 0 = no match, 1 = initials match (highest priority), 2 = name match
  const getMatchScore = useCallback((initials: string, query: string): number => {
    if (initials.toLowerCase().includes(query)) return 1; // initials match - highest priority
    const member = membersByInitials.get(initials.toLowerCase());
    if (member) {
      if (member.firstName.toLowerCase().includes(query) ||
          member.lastName.toLowerCase().includes(query)) {
        return 2; // name match - lower priority
      }
    }
    return 0; // no match
  }, [membersByInitials]);

  const matchesQuery = useCallback((initials: string, query: string): boolean => {
    return getMatchScore(initials, query) > 0;
  }, [getMatchScore]);

  const resetState = () => {
    setStep('select-passenger');
    setPassengerSearch('');
    setTargetSearch('');
    setSelectedPassenger(null);
    setTransfers([]);
  };

  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) {
      resetState();
    }
    onOpenChange(newOpen);
  };

  // Get all passengers and drivers from parties
  const { allPassengers, allDrivers, allParties } = useMemo(() => {
    if (!dayPlan) return { allPassengers: [], allDrivers: new Set<string>(), allParties: [] };

    const passengers: { passenger: string; party: Party }[] = [];
    const drivers = new Set<string>();

    dayPlan.parties.forEach(party => {
      drivers.add(party.driver.toLowerCase());
      party.passengers.forEach(p => {
        passengers.push({ passenger: p, party });
      });
    });

    return { allPassengers: passengers, allDrivers: drivers, allParties: dayPlan.parties };
  }, [dayPlan]);

  // Filter passengers based on search, excluding already transferred ones
  // Sort by: initials matches first, then name matches; within each, schoolbound before homebound
  const filteredPassengers = useMemo(() => {
    const query = passengerSearch.trim().toLowerCase();
    if (!query) return [];

    const transferredPassengers = new Set(transfers.map(t => `${t.passenger}-${t.fromParty.driver}-${t.fromParty.time}`));

    return allPassengers
      .filter(({ passenger, party }) => {
        const key = `${passenger}-${party.driver}-${party.time}`;
        if (transferredPassengers.has(key)) return false;
        return matchesQuery(passenger, query);
      })
      .map(item => ({
        ...item,
        matchScore: getMatchScore(item.passenger, query),
      }))
      .sort((a, b) => {
        // Sort by match score first (1 = initials match before 2 = name match)
        if (a.matchScore !== b.matchScore) return a.matchScore - b.matchScore;
        // Then schoolbound before homebound
        if (a.party.schoolbound !== b.party.schoolbound) {
          return a.party.schoolbound ? -1 : 1;
        }
        return 0;
      });
  }, [passengerSearch, allPassengers, transfers, matchesQuery, getMatchScore]);

  // Check if search matches a driver
  const searchMatchesDriver = useMemo(() => {
    const query = passengerSearch.trim().toLowerCase();
    if (!query) return false;
    return Array.from(allDrivers).some(d => matchesQuery(d, query));
  }, [passengerSearch, allDrivers, matchesQuery]);

  // Filter target parties based on search
  // Sort by: initials matches first, then name matches; within each, schoolbound before homebound
  const filteredTargetParties = useMemo(() => {
    if (!selectedPassenger) return [];
    const query = targetSearch.trim().toLowerCase();
    if (!query) return [];

    return allParties
      .filter(party => {
        // Exclude the current party
        if (party.driver === selectedPassenger.party.driver && party.time === selectedPassenger.party.time) {
          return false;
        }
        // Must match same direction (schoolbound)
        if (party.schoolbound !== selectedPassenger.party.schoolbound) {
          return false;
        }
        // Match driver or any passenger by name or initials
        const matchesDriver = matchesQuery(party.driver, query);
        const matchesPassenger = party.passengers.some(p => matchesQuery(p, query));
        return matchesDriver || matchesPassenger;
      })
      .map(party => {
        // Get best match score (lowest = highest priority)
        const driverScore = getMatchScore(party.driver, query);
        const passengerScores = party.passengers.map(p => getMatchScore(p, query)).filter(s => s > 0);
        const bestScore = Math.min(
          driverScore || 999,
          ...passengerScores.map(s => s || 999)
        );
        return { party, matchScore: bestScore === 999 ? 2 : bestScore };
      })
      .sort((a, b) => {
        // Sort by match score first (1 = initials match before 2 = name match)
        if (a.matchScore !== b.matchScore) return a.matchScore - b.matchScore;
        // Then schoolbound before homebound
        if (a.party.schoolbound !== b.party.schoolbound) {
          return a.party.schoolbound ? -1 : 1;
        }
        return 0;
      })
      .map(item => item.party);
  }, [targetSearch, allParties, selectedPassenger, matchesQuery, getMatchScore]);

  const handleSelectPassenger = (passenger: string, party: Party) => {
    setSelectedPassenger({ passenger, party });
    setPassengerSearch('');
    setTargetSearch('');
    setStep('select-target');
  };

  const handleSelectTargetParty = (targetParty: Party) => {
    if (!selectedPassenger) return;

    const hasTimeWarning = targetParty.time !== selectedPassenger.party.time;

    const newTransfer: Transfer = {
      id: `${Date.now()}-${Math.random()}`,
      passenger: selectedPassenger.passenger,
      fromParty: selectedPassenger.party,
      toParty: targetParty,
      hasTimeWarning,
    };

    setTransfers(prev => [...prev, newTransfer]);
    setSelectedPassenger(null);
    setTargetSearch('');
    setStep('select-passenger');
  };

  const handleRemoveTransfer = (id: string) => {
    setTransfers(prev => prev.filter(t => t.id !== id));
  };

  const handleCancelPassengerSelection = () => {
    setSelectedPassenger(null);
    setTargetSearch('');
    setStep('select-passenger');
  };

  const handleApply = () => {
    if (!dayPlan || transfers.length === 0) return;
    onApplyTransfers(dayPlan, transfers);
    handleOpenChange(false);
  };

  if (!dayPlan) return null;

  const dayLabel = `${DAY_NAMES[dayPlan.dayOfWeekABCombo.dayOfWeek]} (Week ${dayPlan.dayOfWeekABCombo.isWeekA ? 'A' : 'B'})`;

  // Separate parties by direction for the preview
  const schoolboundParties = dayPlan.parties
    .filter(p => p.schoolbound === true)
    .sort((a, b) => a.time - b.time);
  const homeboundParties = dayPlan.parties
    .filter(p => p.schoolbound === false)
    .sort((a, b) => a.time - b.time);

  const renderPartyPreview = (party: Party) => (
    <div key={`${party.driver}-${party.time}`} className="text-xs py-1 border-b border-border/30 last:border-b-0">
      <span className="font-mono text-muted-foreground">[{formatTime(party.time)}]</span>
      {' '}
      <span className="font-medium">{formatPerson(party.driver)}</span>
      {party.passengers.length > 0 && (
        <span className="text-muted-foreground"> · {party.passengers.map(p => formatPerson(p)).join(' · ')}</span>
      )}
    </div>
  );

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-4xl">
        <DialogHeader>
          <DialogTitle>Edit Day Plan - {dayLabel}</DialogTitle>
        </DialogHeader>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Left side: Day Plan Preview */}
          <div className="space-y-4">
            <p className="text-sm font-medium text-foreground">Current Schedule</p>
            <div className="rounded-lg border border-border/50 bg-muted/30 p-3 space-y-4">
              {/* Schoolbound */}
              <div>
                <p className="text-xs font-semibold text-muted-foreground mb-2">Schoolbound</p>
                <ScrollArea className="max-h-40">
                  {schoolboundParties.length > 0 ? (
                    schoolboundParties.map(renderPartyPreview)
                  ) : (
                    <p className="text-xs text-muted-foreground">—</p>
                  )}
                </ScrollArea>
              </div>
              {/* Homebound */}
              <div>
                <p className="text-xs font-semibold text-muted-foreground mb-2">Homebound</p>
                <ScrollArea className="max-h-40">
                  {homeboundParties.length > 0 ? (
                    homeboundParties.map(renderPartyPreview)
                  ) : (
                    <p className="text-xs text-muted-foreground">—</p>
                  )}
                </ScrollArea>
              </div>
            </div>
          </div>

          {/* Right side: Transfer Controls */}
          <div className="space-y-4">
            {/* Pending Transfers */}
            {transfers.length > 0 && (
              <div className="space-y-2">
                <p className="text-sm font-medium text-foreground">Pending Transfers</p>
                <div className="space-y-2 max-h-32 overflow-y-auto">
                  {transfers.map(transfer => (
                    <div
                      key={transfer.id}
                      className="flex items-center gap-2 p-2 rounded-md bg-muted/50 border border-border/50 text-sm"
                    >
                      <span className="font-medium">{formatPerson(transfer.passenger)}</span>
                      <span className="text-muted-foreground text-xs font-mono">
                        [{formatTime(transfer.fromParty.time)}]
                      </span>
                      <ArrowRight className="h-3 w-3 text-muted-foreground flex-shrink-0" />
                      <span className="text-muted-foreground text-xs font-mono">
                        [{formatTime(transfer.toParty.time)}]
                      </span>
                      <span className="text-muted-foreground text-xs">
                        {formatPerson(transfer.toParty.driver)}
                      </span>
                      {transfer.hasTimeWarning && (
                        <AlertTriangle className="h-3.5 w-3.5 text-yellow-500 flex-shrink-0" />
                      )}
                      <button
                        onClick={() => handleRemoveTransfer(transfer.id)}
                        className="ml-auto p-1 rounded hover:bg-destructive/10 text-destructive"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Step 1: Select Passenger */}
            {step === 'select-passenger' && (
              <div className="space-y-3">
                <p className="text-sm text-muted-foreground">
                  Search for a passenger to move to another party
                </p>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Search by name or initials..."
                    value={passengerSearch}
                    onChange={(e) => setPassengerSearch(e.target.value)}
                    className="pl-9"
                    autoFocus
                  />
                </div>

                {passengerSearch.trim() && (
                  <div className="space-y-1 max-h-48 overflow-y-auto">
                    {filteredPassengers.length > 0 ? (
                      filteredPassengers.map(({ passenger, party }) => (
                        <button
                          key={`${passenger}-${party.driver}-${party.time}`}
                          onClick={() => handleSelectPassenger(passenger, party)}
                          className="w-full text-left p-2 rounded-md hover:bg-muted transition-colors text-sm"
                        >
                          <span className="font-medium">{formatPerson(passenger)}</span>
                          <span className="text-muted-foreground ml-2">
                            riding with {formatPerson(party.driver)} <span className="font-mono">[{formatTime(party.time)}]</span>
                            {party.schoolbound ? ' (schoolbound)' : ' (homebound)'}
                          </span>
                        </button>
                      ))
                    ) : searchMatchesDriver ? (
                      <div className="p-3 rounded-md bg-muted/50 border border-border/50 text-sm text-muted-foreground">
                        <AlertTriangle className="h-4 w-4 inline-block mr-2 text-yellow-500" />
                        This person is a driver and cannot be moved. Only passengers can be transferred.
                      </div>
                    ) : (
                      <p className="text-sm text-muted-foreground p-2">No passengers found</p>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Step 2: Select Target Party */}
            {step === 'select-target' && selectedPassenger && (
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <Badge variant="secondary" className="gap-1">
                    {formatPerson(selectedPassenger.passenger)}
                    <button onClick={handleCancelPassengerSelection} className="ml-1">
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                  <span className="text-sm text-muted-foreground">
                    from {formatPerson(selectedPassenger.party.driver)} <span className="font-mono">[{formatTime(selectedPassenger.party.time)}]</span>
                  </span>
                </div>

                <p className="text-sm text-muted-foreground">
                  Search for the target party (by driver or passenger name)
                </p>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Search target party..."
                    value={targetSearch}
                    onChange={(e) => setTargetSearch(e.target.value)}
                    className="pl-9"
                    autoFocus
                  />
                </div>

                {targetSearch.trim() && (
                  <div className="space-y-1 max-h-48 overflow-y-auto">
                    {filteredTargetParties.length > 0 ? (
                      filteredTargetParties.map(party => {
                        const hasTimeWarning = party.time !== selectedPassenger.party.time;
                        return (
                          <button
                            key={`${party.driver}-${party.time}`}
                            onClick={() => handleSelectTargetParty(party)}
                            className={cn(
                              "w-full text-left p-2 rounded-md hover:bg-muted transition-colors text-sm",
                              hasTimeWarning && "border border-yellow-500/30"
                            )}
                          >
                            <div className="flex items-center gap-2">
                              <span className="font-medium">{formatPerson(party.driver)}</span>
                              <span className="text-muted-foreground font-mono">
                                [{formatTime(party.time)}]
                              </span>
                              {hasTimeWarning && (
                                <AlertTriangle className="h-3.5 w-3.5 text-yellow-500" />
                              )}
                            </div>
                            {party.passengers.length > 0 && (
                              <p className="text-xs text-muted-foreground mt-0.5">
                                with {party.passengers.map(p => formatPerson(p)).join(', ')}
                              </p>
                            )}
                            {hasTimeWarning && (
                              <p className="text-xs text-yellow-600 mt-1">
                                Different time: <span className="font-mono">{formatTime(selectedPassenger.party.time)}</span> → <span className="font-mono">{formatTime(party.time)}</span>
                              </p>
                            )}
                          </button>
                        );
                      })
                    ) : (
                      <p className="text-sm text-muted-foreground p-2">
                        No matching parties found (same direction only)
                      </p>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button variant="outline" onClick={() => handleOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleApply}
            disabled={transfers.length === 0}
          >
            Apply {transfers.length > 0 && `(${transfers.length})`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
