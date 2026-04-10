import { useState, useMemo } from 'react';
import { Member, MemberViewMode, CustomDay } from '@/types/carpool';
import { MemberCard } from './MemberCard';
import { MemberListItem } from './MemberListItem';
import { MemberDialog } from './MemberDialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { 
  Plus, 
  Search, 
  LayoutGrid, 
  List, 
  Download, 
  Upload,
  ListChecks,
  Users,
  CalendarDays
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

const WEEKDAY_LABELS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];

const isExplicitCustomDay = (day: CustomDay) => {
  return !!(
    day.ignoreCompletely ||
    day.noWaitingAfternoon ||
    day.needsCar ||
    day.drivingSkip ||
    day.skipMorning ||
    day.skipAfternoon ||
    day.customStart ||
    day.customEnd
  );
};

const summarizeCustomDay = (day: CustomDay) => {
  if (day.ignoreCompletely) return 'Skip';

  const labels: string[] = [];
  const hasSoloSegment = day.skipMorning || day.skipAfternoon;

  if (day.needsCar && !hasSoloSegment) labels.push('Needs car');
  if (day.drivingSkip) labels.push('No car');
  if (day.skipMorning) labels.push('Solo AM');
  if (day.skipAfternoon) labels.push('Solo PM');
  if (day.noWaitingAfternoon) labels.push('No wait PM');
  if (day.customStart) labels.push(`Start ${day.customStart}`);
  if (day.customEnd) labels.push(`End ${day.customEnd}`);
  return labels.join(', ');
};

const buildMemberCustomPrefLines = (member: Member) => {
  if (!member.customDays) return [];

  const byWeekday = new Map<number, { a?: string; b?: string }>();

  for (const [dayKey, day] of Object.entries(member.customDays)) {
    if (!isExplicitCustomDay(day)) continue;

    const numericKey = Number(dayKey);
    if (!Number.isInteger(numericKey) || numericKey < 0 || numericKey > 9) continue;

    const weekdayIndex = numericKey % 5;
    const week = numericKey < 5 ? 'a' : 'b';
    const summary = summarizeCustomDay(day);
    if (!summary) continue;

    const current = byWeekday.get(weekdayIndex) ?? {};
    current[week] = summary;
    byWeekday.set(weekdayIndex, current);
  }

  const lines: string[] = [];

  for (let weekdayIndex = 0; weekdayIndex < 5; weekdayIndex += 1) {
    const entry = byWeekday.get(weekdayIndex);
    if (!entry) continue;

    const dayLabel = WEEKDAY_LABELS[weekdayIndex];
    if (entry.a && entry.b && entry.a === entry.b) {
      lines.push(`${dayLabel} (A+B): ${entry.a}`);
      continue;
    }

    if (entry.a) lines.push(`${dayLabel} (A): ${entry.a}`);
    if (entry.b) lines.push(`${dayLabel} (B): ${entry.b}`);
  }

  return lines;
};

interface MembersPanelProps {
  members: Member[];
  onMembersChange: (members: Member[]) => void;
  hasPlan: boolean;
  onNavigateToPlan: () => void;
}

export function MembersPanel({ members, onMembersChange, hasPlan, onNavigateToPlan }: MembersPanelProps) {
  const [viewMode, setViewMode] = useState<MemberViewMode>('card');
  const [searchQuery, setSearchQuery] = useState('');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [customPrefsOpen, setCustomPrefsOpen] = useState(false);
  const [editingMember, setEditingMember] = useState<Member | null>(null);
  const [deletingMember, setDeletingMember] = useState<Member | null>(null);
  const [dialogInitialTab, setDialogInitialTab] = useState<'basic' | 'custom'>('basic');
  const { toast } = useToast();

// Utility function to sort members alphabetically
const sortMembers = (membersList: Member[]) => {
    return [...membersList].sort((a, b) => {
        const lastNameCompare = a.lastName.localeCompare(b.lastName);
        if (lastNameCompare !== 0) return lastNameCompare;
        return a.firstName.localeCompare(b.firstName);
    });
};

  const filteredMembers = useMemo(() => {
    if (!searchQuery.trim()) return members;
    const q = searchQuery.toLowerCase();
    return members.filter(m => 
      m.firstName.toLowerCase().includes(q) ||
      m.lastName.toLowerCase().includes(q) ||
      m.initials.toLowerCase().includes(q)
    );
  }, [members, searchQuery]);

  const membersWithCustomPrefs = useMemo(() => {
    return members
      .map((member) => {
        const lines = buildMemberCustomPrefLines(member);
        return {
          member,
          lines,
        };
      })
      .filter((item) => item.lines.length > 0);
  }, [members]);

  const handleAddMember = () => {
    setEditingMember(null);
    setDialogOpen(true);
  };

  const handleEditMember = (member: Member) => {
    setEditingMember(member);
    setDialogInitialTab('basic');
    setDialogOpen(true);
  };

  const handleEditCustom = (member: Member) => {
    setEditingMember(member);
    setDialogInitialTab('custom');
    setDialogOpen(true);
  };

  const handleSaveMember = (member: Member) => {
    if (editingMember) {
      const updatedMembers = members.map(m => 
        m.initials === editingMember.initials ? member : m
      );
      onMembersChange(sortMembers(updatedMembers));
      toast({ title: 'Member updated', description: `${member.firstName} ${member.lastName} has been updated.` });
    } else {
      if (members.some(m => m.initials === member.initials)) {
        toast({ 
          title: 'Duplicate initials', 
          description: 'A member with these initials already exists.',
          variant: 'destructive'
        });
        return;
      }
      onMembersChange(sortMembers([...members, member]));
      toast({ title: 'Member added', description: `${member.firstName} ${member.lastName} has been added.` });
    }
  };

  const handleDeleteMember = (member: Member) => {
    setDeletingMember(member);
  };

  const confirmDelete = () => {
    if (deletingMember) {
      onMembersChange(members.filter(m => m.initials !== deletingMember.initials));
      toast({ title: 'Member removed', description: `${deletingMember.firstName} ${deletingMember.lastName} has been removed.` });
      setDeletingMember(null);
    }
  };

  const handleExport = () => {
    const data = JSON.stringify(members, null, 2);
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'carpool-members.json';
    a.click();
    URL.revokeObjectURL(url);
    toast({ title: 'Exported', description: `${members.length} members exported to JSON.` });
  };

  const handleImport = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;
      try {
        const text = await file.text();
        const imported = JSON.parse(text) as Member[];
        if (!Array.isArray(imported)) throw new Error('Invalid format');
        
        // Clean up customDays: remove entries that are equal to the default empty value
        const cleanedMembers = imported.map(member => {
          if (!member.customDays) return member;
          
          const cleanedCustomDays: Record<string, CustomDay> = {};
          for (const [dayKey, day] of Object.entries(member.customDays)) {
            const isDefault = 
              !day.ignoreCompletely &&
              !day.noWaitingAfternoon &&
              !day.needsCar &&
              !day.drivingSkip &&
              !day.skipMorning &&
              !day.skipAfternoon &&
              !day.customStart &&
              !day.customEnd;
            
            if (!isDefault) {
              cleanedCustomDays[dayKey] = day;
            }
          }
          
          return {
            ...member,
            customDays: Object.keys(cleanedCustomDays).length > 0 ? cleanedCustomDays : undefined
          };
        });
        
        onMembersChange(sortMembers(cleanedMembers));
        toast({ title: 'Imported', description: `${cleanedMembers.length} members imported.` });
      } catch (err) {
        toast({ 
          title: 'Import failed', 
          description: 'The file could not be parsed. Please check the format.',
          variant: 'destructive'
        });
      }
    };
    input.click();
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search members..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>
        
        <div className="flex items-center gap-2">
          <div className="flex items-center bg-muted/50 rounded-lg p-1">
            <Button
              variant={viewMode === 'card' ? 'secondary' : 'ghost'}
              size="icon"
              onClick={() => setViewMode('card')}
              className="h-8 w-8"
            >
              <LayoutGrid className="h-4 w-4" />
            </Button>
            <Button
              variant={viewMode === 'list' ? 'secondary' : 'ghost'}
              size="icon"
              onClick={() => setViewMode('list')}
              className="h-8 w-8"
            >
              <List className="h-4 w-4" />
            </Button>
          </div>
          
          <Button variant="outline" size="icon" onClick={handleImport} aria-label="Import" title="Import">
            <Upload className="h-4 w-4" />
          </Button>
          <Button variant="outline" size="icon" onClick={handleExport} disabled={members.length === 0} aria-label="Export" title="Export">
            <Download className="h-4 w-4" />
          </Button>
          <Button variant="outline" size="sm" onClick={() => setCustomPrefsOpen(true)}>
            <ListChecks className="h-4 w-4 mr-2" />
            Custom Prefs
          </Button>
          <Button onClick={handleAddMember}>
            <Plus className="h-4 w-4 mr-2" />
            Add Member
          </Button>
        </div>
      </div>

      {filteredMembers.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <div className="h-16 w-16 rounded-2xl bg-muted flex items-center justify-center mb-4">
            <Users className="h-8 w-8 text-muted-foreground" />
          </div>
          <h3 className="font-medium text-lg text-foreground mb-1">
            {members.length === 0 ? 'No members yet' : 'No results found'}
          </h3>
          <p className="text-muted-foreground text-sm max-w-sm">
            {members.length === 0 
              ? 'Add your first carpool member to get started, or import from a JSON file.'
              : 'Try adjusting your search query.'}
          </p>
          {members.length === 0 && (
            <Button onClick={handleAddMember} className="mt-4">
              <Plus className="h-4 w-4 mr-2" />
              Add First Member
            </Button>
          )}
        </div>
      ) : viewMode === 'card' ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredMembers.map((member) => (
            <MemberCard
              key={member.initials}
              member={member}
              onEdit={handleEditMember}
              onEditCustom={handleEditCustom}
              onDelete={handleDeleteMember}
            />
          ))}
        </div>
      ) : (
        <div className="border border-border rounded-xl bg-card divide-y divide-border">
          {filteredMembers.map((member) => (
            <MemberListItem
              key={member.initials}
              member={member}
              onEdit={handleEditMember}
              onEditCustom={handleEditCustom}
              onDelete={handleDeleteMember}
            />
          ))}
        </div>
      )}
      {/* Navigation to Plan */}
      {filteredMembers.length > 0 && (
        <div className="flex justify-center pt-4 mt-4 border-t border-border">
          <Button onClick={onNavigateToPlan} size="lg" variant="gradient">
            <CalendarDays className="h-4 w-4 mr-2" />
            {hasPlan ? 'Back to Driving Plan' : 'Generate or Load Driving Plan'}
          </Button>
        </div>
      )}
      <MemberDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        member={editingMember}
        onSave={handleSaveMember}
        initialTab={dialogInitialTab}
      />

      <Dialog open={customPrefsOpen} onOpenChange={setCustomPrefsOpen}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>Custom Preferences Overview</DialogTitle>
            <DialogDescription>
              Overview of all members with explicit custom preferences.
            </DialogDescription>
          </DialogHeader>

          {membersWithCustomPrefs.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No explicit custom preferences found.
            </p>
          ) : (
            <div className="max-h-[60vh] overflow-y-auto pr-1 space-y-1.5">
              {membersWithCustomPrefs.map(({ member, lines }) => (
                <div key={member.initials} className="rounded-lg border border-border p-2">
                  <div className="grid grid-cols-[minmax(140px,220px)_1fr] gap-x-12 items-start">
                    <p className="font-medium text-sm leading-6">{member.firstName} {member.lastName}</p>
                    <div className="space-y-0.2">
                    {lines.map((line) => (
                      <p key={`${member.initials}-${line}`} className="text-sm text-muted-foreground">
                        {line}
                      </p>
                    ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </DialogContent>
      </Dialog>

      <AlertDialog open={!!deletingMember} onOpenChange={() => setDeletingMember(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remove member?</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to remove {deletingMember?.firstName} {deletingMember?.lastName} from the carpool? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={confirmDelete} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
              Remove
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
