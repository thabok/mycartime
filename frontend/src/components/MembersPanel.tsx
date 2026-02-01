import { useState, useMemo } from 'react';
import { Member, MemberViewMode, CustomDay } from '@/types/carpool';
import { MemberCard } from './MemberCard';
import { MemberListItem } from './MemberListItem';
import { MemberDialog } from './MemberDialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
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
  Users,
  CalendarDays
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

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
          
          <Button variant="outline" size="sm" onClick={handleImport}>
            <Upload className="h-4 w-4 mr-2" />
            Import
          </Button>
          <Button variant="outline" size="sm" onClick={handleExport} disabled={members.length === 0}>
            <Download className="h-4 w-4 mr-2" />
            Export
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
