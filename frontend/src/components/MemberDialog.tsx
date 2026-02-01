import { useState, useEffect } from 'react';
import { Member, CustomDay } from '@/types/carpool';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Checkbox } from '@/components/ui/checkbox';

interface MemberDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  member?: Member | null;
  onSave: (member: Member) => void;
  initialTab?: 'basic' | 'custom';
}

const WEEK_A_DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'];
const WEEK_B_DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'];

const createEmptyCustomDay = (): CustomDay => ({
  ignoreCompletely: false,
  noWaitingAfternoon: false,
  needsCar: false,
  drivingSkip: false,
  skipMorning: false,
  skipAfternoon: false,
  customStart: '',
  customEnd: '',
});

export function MemberDialog({ open, onOpenChange, member, onSave, initialTab = 'basic' }: MemberDialogProps) {
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [initials, setInitials] = useState('');
  const [numberOfSeats, setNumberOfSeats] = useState(4);
  const [isPartTime, setIsPartTime] = useState(false);
  const [customDays, setCustomDays] = useState<Record<string, CustomDay>>({});
  const [activeTab, setActiveTab] = useState('basic');

  useEffect(() => {
    if (member) {
      setFirstName(member.firstName);
      setLastName(member.lastName);
      setInitials(member.initials);
      setNumberOfSeats(member.numberOfSeats);
      setIsPartTime(member.isPartTime || false);
      setCustomDays(member.customDays || {});
    } else {
      setFirstName('');
      setLastName('');
      setInitials('');
      setNumberOfSeats(4);
      setIsPartTime(false);
      setCustomDays({});
    }
    setActiveTab(initialTab);
  }, [member, open, initialTab]);

  useEffect(() => {
    if (!member && firstName && lastName) {
      const auto = `${firstName.charAt(0)}${lastName.charAt(0)}`.toUpperCase();
      setInitials(auto);
    }
  }, [firstName, lastName, member]);

  const handleSave = () => {
    const cleanedCustomDays: Record<string, CustomDay> = {};
    Object.entries(customDays).forEach(([key, day]) => {
      const isEmpty = !day.ignoreCompletely && !day.noWaitingAfternoon && !day.needsCar && 
                      !day.drivingSkip && !day.skipMorning && !day.skipAfternoon && 
                      !day.customStart && !day.customEnd;
      if (!isEmpty) {
        cleanedCustomDays[key] = day;
      }
    });

    onSave({
      firstName: firstName.trim(),
      lastName: lastName.trim(),
      initials: initials.trim(),
      numberOfSeats,
      isPartTime,
      customDays: Object.keys(cleanedCustomDays).length > 0 ? cleanedCustomDays : undefined,
    });
    onOpenChange(false);
  };

  const updateCustomDay = (dayIndex: string, field: keyof CustomDay, value: boolean | string) => {
    setCustomDays(prev => {
      const currentDay = prev[dayIndex] || createEmptyCustomDay();
      const updatedDay = { ...currentDay };
      
      // Apply the direct change
      updatedDay[field] = value as never;
      
      // Frontend logic for custom day preferences
      if (field === 'needsCar' && value === true) {
        // Needs Car is mutually exclusive with No car
        updatedDay.drivingSkip = false;
      } else if (field === 'drivingSkip' && value === true) {
        // No car is mutually exclusive with Needs Car
        updatedDay.needsCar = false;
      } else if (field === 'skipMorning' && value === true) {
        // Skip AM implicitly activates Needs Car
        updatedDay.needsCar = true;
      } else if (field === 'skipAfternoon' && value === true) {
        // Skip PM implicitly activates Needs Car and deactivates No wait PM
        updatedDay.needsCar = true;
        updatedDay.noWaitingAfternoon = false;
      } else if (field === 'noWaitingAfternoon' && value === true) {
        // No wait PM is mutually exclusive with Skip PM
        updatedDay.skipAfternoon = false;
      }
      
      return {
        ...prev,
        [dayIndex]: updatedDay
      };
    });
  };

  const isValid = firstName.trim() && lastName.trim() && initials.trim() && numberOfSeats > 0;

  const dialogWidth = activeTab === 'custom' ? 'sm:max-w-4xl' : 'sm:max-w-lg';

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className={dialogWidth}>
        <DialogHeader>
          <DialogTitle>{member ? 'Edit Member' : 'Add New Member'}</DialogTitle>
        </DialogHeader>
        
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="basic">Basic Info</TabsTrigger>
            <TabsTrigger value="custom">Custom Days</TabsTrigger>
          </TabsList>
          
          <TabsContent value="basic" className="space-y-4 mt-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="firstName">First Name</Label>
                <Input
                  id="firstName"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  placeholder="John"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="lastName">Last Name</Label>
                <Input
                  id="lastName"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  placeholder="Smith"
                />
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="initials">Initials</Label>
                <Input
                  id="initials"
                  value={initials}
                  onChange={(e) => setInitials(e.target.value.toUpperCase())}
                  placeholder="JS"
                  maxLength={3}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="seats">Number of Seats</Label>
                <Input
                  id="seats"
                  type="number"
                  min={1}
                  max={9}
                  value={numberOfSeats}
                  onChange={(e) => setNumberOfSeats(parseInt(e.target.value) || 1)}
                />
              </div>
            </div>
            
            <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
              <div>
                <Label htmlFor="partTime" className="text-sm font-medium">Part-time</Label>
                <p className="text-xs text-muted-foreground">Member works part-time schedule</p>
              </div>
              <Switch
                id="partTime"
                checked={isPartTime}
                onCheckedChange={setIsPartTime}
              />
            </div>
          </TabsContent>
          
          <TabsContent value="custom" className="mt-4 space-y-4">
            {/* Week A Row */}
            <div>
              <h4 className="text-sm font-medium text-muted-foreground mb-2">Week A</h4>
              <div className="grid grid-cols-5 gap-2">
                {WEEK_A_DAYS.map((dayName, index) => {
                  const dayKey = index.toString();
                  const day = customDays[dayKey] || createEmptyCustomDay();
                  
                  return (
                    <div key={dayKey} className="border border-border rounded-lg p-2">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium text-xs">{dayName}</span>
                        <div className="flex items-center gap-1">
                          <Checkbox
                            id={`ignore-${dayKey}`}
                            checked={day.ignoreCompletely}
                            onCheckedChange={(checked) => updateCustomDay(dayKey, 'ignoreCompletely', !!checked)}
                            className="h-3 w-3"
                          />
                          <Label htmlFor={`ignore-${dayKey}`} className="text-[10px] text-muted-foreground">
                            Skip
                          </Label>
                        </div>
                      </div>
                      
                      {!day.ignoreCompletely && (
                        <div className="space-y-1.5 text-xs">
                          <label className="flex items-center gap-1.5 cursor-pointer">
                            <Checkbox checked={day.needsCar} onCheckedChange={(checked) => updateCustomDay(dayKey, 'needsCar', !!checked)} className="h-3.5 w-3.5" />
                            Needs car
                          </label>
                          <label className="flex items-center gap-1.5 cursor-pointer">
                            <Checkbox checked={day.skipMorning} onCheckedChange={(checked) => updateCustomDay(dayKey, 'skipMorning', !!checked)} className="h-3.5 w-3.5" />
                            Skip AM
                          </label>
                          <label className="flex items-center gap-1.5 cursor-pointer">
                            <Checkbox checked={day.skipAfternoon} onCheckedChange={(checked) => updateCustomDay(dayKey, 'skipAfternoon', !!checked)} className="h-3.5 w-3.5" />
                            Skip PM
                          </label>
                          <label className="flex items-center gap-1.5 cursor-pointer">
                            <Checkbox checked={day.drivingSkip} onCheckedChange={(checked) => updateCustomDay(dayKey, 'drivingSkip', !!checked)} className="h-3.5 w-3.5" />
                            No car
                          </label>
                          <label className="flex items-center gap-1.5 cursor-pointer">
                            <Checkbox checked={day.noWaitingAfternoon} onCheckedChange={(checked) => updateCustomDay(dayKey, 'noWaitingAfternoon', !!checked)} className="h-3.5 w-3.5" />
                            No wait PM
                          </label>
                          <div className="flex gap-1 mt-2">
                            <Input type="time" value={day.customStart} onChange={(e) => updateCustomDay(dayKey, 'customStart', e.target.value)} className="h-5 text-[10px] px-0.5 w-full rounded" placeholder="Start" />
                            <Input type="time" value={day.customEnd} onChange={(e) => updateCustomDay(dayKey, 'customEnd', e.target.value)} className="h-5 text-[10px] px-0.5 w-full rounded" placeholder="End" />
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Week B Row */}
            <div>
              <h4 className="text-sm font-medium text-muted-foreground mb-2">Week B</h4>
              <div className="grid grid-cols-5 gap-2">
                {WEEK_B_DAYS.map((dayName, index) => {
                  const dayKey = (index + 5).toString();
                  const day = customDays[dayKey] || createEmptyCustomDay();
                  
                  return (
                    <div key={dayKey} className="border border-border rounded-lg p-2">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium text-xs">{dayName}</span>
                        <div className="flex items-center gap-1">
                          <Checkbox
                            id={`ignore-${dayKey}`}
                            checked={day.ignoreCompletely}
                            onCheckedChange={(checked) => updateCustomDay(dayKey, 'ignoreCompletely', !!checked)}
                            className="h-3 w-3"
                          />
                          <Label htmlFor={`ignore-${dayKey}`} className="text-[10px] text-muted-foreground">
                            Skip
                          </Label>
                        </div>
                      </div>
                      
                      {!day.ignoreCompletely && (
                        <div className="space-y-1.5 text-xs">
                          <label className="flex items-center gap-1.5 cursor-pointer">
                            <Checkbox checked={day.skipMorning} onCheckedChange={(checked) => updateCustomDay(dayKey, 'skipMorning', !!checked)} className="h-3.5 w-3.5" />
                            Skip AM
                          </label>
                          <label className="flex items-center gap-1.5 cursor-pointer">
                            <Checkbox checked={day.skipAfternoon} onCheckedChange={(checked) => updateCustomDay(dayKey, 'skipAfternoon', !!checked)} className="h-3.5 w-3.5" />
                            Skip PM
                          </label>
                          <label className="flex items-center gap-1.5 cursor-pointer">
                            <Checkbox checked={day.needsCar} onCheckedChange={(checked) => updateCustomDay(dayKey, 'needsCar', !!checked)} className="h-3.5 w-3.5" />
                            Needs car
                          </label>
                          <label className="flex items-center gap-1.5 cursor-pointer">
                            <Checkbox checked={day.drivingSkip} onCheckedChange={(checked) => updateCustomDay(dayKey, 'drivingSkip', !!checked)} className="h-3.5 w-3.5" />
                            Skip driving
                          </label>
                          <label className="flex items-center gap-1.5 cursor-pointer">
                            <Checkbox checked={day.noWaitingAfternoon} onCheckedChange={(checked) => updateCustomDay(dayKey, 'noWaitingAfternoon', !!checked)} className="h-3.5 w-3.5" />
                            No wait PM
                          </label>
                          <div className="flex gap-1 mt-2 text-[10px] text-muted-foreground">
                            <Input type="time" value={day.customStart} onChange={(e) => updateCustomDay(dayKey, 'customStart', e.target.value)} className="h-5 text-[10px] px-0.5 w-full rounded" placeholder="Start" />
                            <Input type="time" value={day.customEnd} onChange={(e) => updateCustomDay(dayKey, 'customEnd', e.target.value)} className="h-5 text-[10px] px-0.5 w-full rounded" placeholder="End" />
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </TabsContent>
        </Tabs>
        
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={!isValid}>
            {member ? 'Update' : 'Add'} Member
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
