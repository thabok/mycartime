import { Member } from '@/types/carpool';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Car, Trash2, Clock, Settings } from 'lucide-react';

interface MemberListItemProps {
  member: Member;
  onEdit: (member: Member) => void;
  onEditCustom: (member: Member) => void;
  onDelete: (member: Member) => void;
}

export function MemberListItem({ member, onEdit, onEditCustom, onDelete }: MemberListItemProps) {
  const hasCustomDays = member.customDays && Object.keys(member.customDays).length > 0;
  
  return (
    <div 
      className="group flex items-center gap-4 p-3 rounded-lg hover:bg-muted/50 transition-colors animate-fade-in cursor-pointer"
      onClick={() => onEdit(member)}
    >
      <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center text-primary font-semibold text-sm flex-shrink-0">
        {member.initials}
      </div>
      
      <div className="flex-1 min-w-0">
        <h3 className="font-medium text-foreground truncate">
          {member.firstName} {member.lastName}
        </h3>
      </div>
      
      <div className="flex items-center gap-3 text-sm text-muted-foreground">
        <div className="flex items-center gap-1">
          <Car className="h-3.5 w-3.5" />
          <span>{member.numberOfSeats}</span>
        </div>
        
        {member.isPartTime && (
          <Badge variant="secondary" className="text-xs">
            <Clock className="h-3 w-3 mr-1" />
            PT
          </Badge>
        )}
        
        {hasCustomDays && (
          <Badge variant="outline" className="text-xs">
            <Settings className="h-3 w-3 mr-1" />
            {Object.keys(member.customDays!).length}
          </Badge>
        )}
      </div>
      
      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <Button
          variant="ghost"
          size="icon"
          onClick={(e) => { e.stopPropagation(); onDelete(member); }}
          className="h-8 w-8 text-muted-foreground hover:text-destructive"
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
