package entities;
public class Car {

    private boolean isSmall;
    private int noSeats;
    
    public Car() {
    }
    
	public boolean isSmall() {
		return isSmall;
	}
	public void setSmall(boolean isSmall) {
		this.isSmall = isSmall;
	}
	public int getNoSeats() {
		return noSeats;
	}
	public int getNoPassengerSeats() {
		return noSeats - 1;
	}
	public void setNoSeats(int noSeats) {
		this.noSeats = noSeats;
	}

	public String toString() {
		return (isSmall ? "Small" : "Roomy") + " car with " + noSeats + " seats";
	}
	
}
