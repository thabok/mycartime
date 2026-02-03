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
  poolName?: string;
}

export interface TimeInfo {
  timetableTime: number | null;
  customPrefTime: number | null;
  effectiveTime: number;
}

export interface DayPlan {
  dayOfWeekABCombo: DayOfWeekABCombo;
  parties: Party[];
  schoolboundTimesByInitials: Record<string, number>;
  homeboundTimesByInitials: Record<string, number>;
  schoolboundTimeInfoByInitials?: Record<string, TimeInfo>;
  homeboundTimeInfoByInitials?: Record<string, TimeInfo>;
}

export interface DrivingPlan {
  summary: string;
  dayPlans: Record<string, DayPlan>;
  memberIdMap?: Record<string, string>;
  scheduleUrlTemplate?: string;
}

export type ViewMode = 'members' | 'plan';
export type MemberViewMode = 'card' | 'list';
