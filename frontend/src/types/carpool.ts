export interface CustomDay {
  ignoreCompletely: boolean;
  noWaitingAfternoon: boolean;
  needsCar: boolean;
  drivingSkip: boolean;
  skipMorning: boolean;
  skipAfternoon: boolean;
  customStart: string;
  customEnd: string;
}

export interface Member {
  firstName: string;
  lastName: string;
  initials: string;
  numberOfSeats: number;
  isPartTime?: boolean;
  customDays?: Record<string, CustomDay>;
}

export interface DayOfWeekABCombo {
  dayOfWeek: 'MONDAY' | 'TUESDAY' | 'WEDNESDAY' | 'THURSDAY' | 'FRIDAY';
  isWeekA: boolean;
  uniqueNumber: number;
}

export interface Party {
  dayOfWeekABCombo: DayOfWeekABCombo;
  driver: string;
  time: number;
  passengers: string[];
  isDesignatedDriver: boolean;
  drivesDespiteCustomPrefs: boolean;
  schoolbound: boolean;
}

export interface DayPlan {
  dayOfWeekABCombo: DayOfWeekABCombo;
  parties: Party[];
  schoolboundTimesByInitials: Record<string, number>;
  homeboundTimesByInitials: Record<string, number>;
}

export interface DrivingPlan {
  summary: string;
  dayPlans: Record<string, DayPlan>;
}

export type ViewMode = 'members' | 'plan';
export type MemberViewMode = 'card' | 'list';
