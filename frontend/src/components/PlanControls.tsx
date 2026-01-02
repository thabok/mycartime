import { useState, useEffect } from 'react';
import { format, isMonday, parseISO } from 'date-fns';
import { Member, DrivingPlan } from '@/types/carpool';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Calendar } from '@/components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { 
  CalendarIcon, 
  Loader2, 
  Sparkles, 
  Upload, 
  Download, 
  FileText,
  Trash2,
  Lock
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useToast } from '@/hooks/use-toast';
import { useLocalStorage } from '@/hooks/useLocalStorage';

interface PlanControlsProps {
  members: Member[];
  plan: DrivingPlan | null;
  onPlanChange: (plan: DrivingPlan | null) => void;
  onViewPlan: () => void;
}

export function PlanControls({ members, plan, onPlanChange, onViewPlan }: PlanControlsProps) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [referenceDateString, setReferenceDateString] = useLocalStorage<string | null>('carpool-reference-date', null);
  const [referenceDate, setReferenceDate] = useState<Date | undefined>(() => {
    if (referenceDateString) {
      try {
        return parseISO(referenceDateString);
      } catch {
        return undefined;
      }
    }
    return undefined;
  });
  const [isGenerating, setIsGenerating] = useState(false);
  const { toast } = useToast();

  // Sync referenceDate state to localStorage whenever it changes
  useEffect(() => {
    if (referenceDate) {
      setReferenceDateString(format(referenceDate, 'yyyy-MM-dd'));
    } else {
      setReferenceDateString(null);
    }
  }, [referenceDate, setReferenceDateString]);

  const isDateValid = referenceDate && isMonday(referenceDate);
  const canGenerate = username.trim() && password.trim() && isDateValid && members.length > 0 && !plan;

  const formatDateForApi = (date: Date): number => {
    const yyyy = date.getFullYear().toString();
    const mm = (date.getMonth() + 1).toString().padStart(2, '0');
    const dd = date.getDate().toString().padStart(2, '0');
    return parseInt(`${yyyy}${mm}${dd}`);
  };

  const handleGenerate = async () => {
    if (!canGenerate || !referenceDate) return;
    
    setIsGenerating(true);
    try {
      const hash = btoa(password);
      const payload = {
        persons: members,
        scheduleReferenceStartDate: formatDateForApi(referenceDate),
        username: username.trim(),
        hash,
      };

      const response = await fetch('http://127.0.0.1:1338/api/v1/drivingplan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(`Server responded with ${response.status}`);
      }

      const generatedPlan = await response.json() as DrivingPlan;
      onPlanChange(generatedPlan);
      onViewPlan();
      toast({ title: 'Plan generated!', description: 'Your driving plan has been created successfully.' });
    } catch (error) {
      console.error('Failed to generate plan:', error);
      toast({ 
        title: 'Generation failed', 
        description: 'Could not connect to the backend service. Please check if it\'s running.',
        variant: 'destructive'
      });
    } finally {
      setIsGenerating(false);
    }
  };

  const handleImportPlan = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;
      try {
        const text = await file.text();
        const imported = JSON.parse(text) as DrivingPlan;
        if (!imported.summary || !imported.dayPlans) throw new Error('Invalid format');
        onPlanChange(imported);
        onViewPlan();
        toast({ title: 'Plan loaded', description: 'Driving plan imported successfully.' });
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

  const handleExportPlan = () => {
    if (!plan) return;
    const data = JSON.stringify(plan, null, 2);
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'driving-plan.json';
    a.click();
    URL.revokeObjectURL(url);
    toast({ title: 'Exported', description: 'Driving plan exported to JSON.' });
  };

  const handleExportPdf = async () => {
    if (!plan) return;
    toast({ 
      title: 'PDF Export', 
      description: 'PDF export requires the backend service. Coming soon!',
    });
  };

  const handleDiscardPlan = () => {
    onPlanChange(null);
    toast({ title: 'Plan discarded', description: 'You can now generate a new plan.' });
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Authentication Card */}
      <Card className="surface-elevated">
        <CardHeader className="pb-4">
          <div className="flex items-center gap-2">
            <Lock className="h-4 w-4 text-primary" />
            <CardTitle className="text-base">Schedule Access</CardTitle>
          </div>
          <CardDescription>
            Enter credentials to fetch teacher schedules from the backend service
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="username">Username</Label>
              <Input
                id="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter username"
                disabled={!!plan}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password"
                disabled={!!plan}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Reference Date Card */}
      <Card className="surface-elevated">
        <CardHeader className="pb-4">
          <div className="flex items-center gap-2">
            <CalendarIcon className="h-4 w-4 text-primary" />
            <CardTitle className="text-base">Reference Date</CardTitle>
          </div>
          <CardDescription>
            Select the Monday that starts Week A of the 2-week cycle
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Popover>
            <PopoverTrigger asChild>
              <Button
                variant="outline"
                className={cn(
                  "w-full justify-start text-left font-normal",
                  !referenceDate && "text-muted-foreground"
                )}
                disabled={!!plan}
              >
                <CalendarIcon className="mr-2 h-4 w-4" />
                {referenceDate ? (
                  <>
                    {format(referenceDate, 'EEEE, MMMM d, yyyy')}
                    {!isMonday(referenceDate) && (
                      <span className="ml-2 text-destructive text-xs">(Must be Monday)</span>
                    )}
                  </>
                ) : (
                  <span>Pick a Monday...</span>
                )}
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0" align="start">
              <Calendar
                mode="single"
                selected={referenceDate}
                onSelect={setReferenceDate}
                className="pointer-events-auto"
                modifiers={{ monday: (date) => isMonday(date) }}
                modifiersStyles={{ monday: { fontWeight: 'bold' } }}
              />
            </PopoverContent>
          </Popover>
          {referenceDate && !isMonday(referenceDate) && (
            <p className="text-xs text-destructive mt-2">
              Please select a Monday as the reference date.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Actions */}
      <div className="space-y-3">
        {!plan ? (
          <>
            <Button
              onClick={handleGenerate}
              disabled={!canGenerate || isGenerating}
              className="w-full"
              variant="gradient"
              size="lg"
            >
              {isGenerating ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Generating Plan...
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4 mr-2" />
                  Generate Driving Plan
                </>
              )}
            </Button>
            
            {!canGenerate && !isGenerating && (
              <p className="text-xs text-muted-foreground text-center">
                {!username.trim() || !password.trim() 
                  ? 'Enter credentials above'
                  : !isDateValid 
                    ? 'Select a Monday as reference date'
                    : members.length === 0 
                      ? 'Add at least one member'
                      : 'A plan already exists'}
              </p>
            )}

            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <span className="w-full border-t" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-background px-2 text-muted-foreground">Or</span>
              </div>
            </div>

            <Button variant="outline" onClick={handleImportPlan} className="w-full">
              <Upload className="h-4 w-4 mr-2" />
              Load Plan from JSON
            </Button>
          </>
        ) : (
          <>
            <Button onClick={onViewPlan} className="w-full" size="lg">
              View Driving Plan
            </Button>
            
            <div className="grid grid-cols-2 gap-2">
              <Button variant="outline" onClick={handleExportPlan}>
                <Download className="h-4 w-4 mr-2" />
                Export JSON
              </Button>
              <Button variant="outline" onClick={handleExportPdf}>
                <FileText className="h-4 w-4 mr-2" />
                Export PDF
              </Button>
            </div>
            
            <Button variant="destructive" onClick={handleDiscardPlan} className="w-full">
              <Trash2 className="h-4 w-4 mr-2" />
              Discard Plan
            </Button>
          </>
        )}
      </div>
    </div>
  );
}
