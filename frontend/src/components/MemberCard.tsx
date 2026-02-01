import { Member } from '@/types/carpool';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Car, Trash2, Clock, Settings } from 'lucide-react';

interface MemberCardProps {
  member: Member;
  onEdit: (member: Member) => void;
  onEditCustom: (member: Member) => void;
  onDelete: (member: Member) => void;
}

export function MemberCard({ member, onEdit, onEditCustom, onDelete }: MemberCardProps) {
  const hasCustomDays = member.customDays && Object.keys(member.customDays).length > 0;
  
  return (
    <Card 
      className="group hover:shadow-lg transition-all duration-200 animate-fade-in cursor-pointer"
      onClick={() => onEdit(member)}
    >
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            {/* <div className="h-16 w-16 rounded-xl bg-primary/10 flex items-center justify-center text-primary font-semibold text-xl shrink-0"> */}
            <div className="h-12 w-12 rounded-xl bg-primary/10 flex items-center justify-center text-primary font-semibold text-lg">
              {member.initials}
            </div>
            <div>
              <h3 className="font-medium text-foreground">
                {member.firstName} {member.lastName}
              </h3>
              <div className="flex items-center gap-2 mt-1">
                <div className="flex items-center gap-1 text-sm text-muted-foreground">
                  <Car className="h-3.5 w-3.5" />
                  <span>{member.numberOfSeats}&nbsp;seats</span>
                </div>
                {member.isPartTime && (
                  <Badge variant="secondary" className="text-xs">
                    <Clock className="h-3 w-3 mr-1" />
                    Part&nbsp;time
                  </Badge>
                )}
              </div>
            </div>
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
        
        {hasCustomDays && (
          <div className="mt-3 pt-3 border-t border-border/50">
            <p className="text-xs text-muted-foreground">
              Custom preferences for {Object.keys(member.customDays!).length} day(s)
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
