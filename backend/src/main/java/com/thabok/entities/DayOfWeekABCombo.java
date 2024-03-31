package com.thabok.entities;

import java.time.DayOfWeek;

public class DayOfWeekABCombo implements Comparable<DayOfWeekABCombo> {
    private DayOfWeek dayOfWeek;
    private boolean isWeekA;
    private int uniqueNumber;
    
    public DayOfWeekABCombo(DayOfWeek dow, boolean isA) {
        this.dayOfWeek = dow;
        this.isWeekA = isA;
        this.setUniqueNumber(dow.getValue() + (isA ? 0 : 7));
    }

    public int getUniqueNumber() {
        return uniqueNumber;
    }

    public void setUniqueNumber(int uniqueNumber) {
        this.uniqueNumber = uniqueNumber;
    }

    public String toString() {
        return dayOfWeek + "_" + (isWeekA ? "A" : "B");
    }

    public DayOfWeek getDayOfWeek() {
        return dayOfWeek;
    }

    public void setDayOfWeek(DayOfWeek dayOfWeek) {
        this.dayOfWeek = dayOfWeek;
    }

    public boolean isWeekA() {
        return isWeekA;
    }

    public void setWeekA(boolean isWeekA) {
        this.isWeekA = isWeekA;
    }

    @Override
    public int compareTo(DayOfWeekABCombo o) {
        return Integer.compare(this.getUniqueNumber(), o.uniqueNumber);
    }
    
}